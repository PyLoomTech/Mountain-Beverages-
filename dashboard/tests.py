import io
import os
import shutil
import tempfile
from datetime import date
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from catalog.models import Category, Product
from core.models import Announcement, Highlight, SiteSettings, TeamMember
from orders.models import Order, OrderItem
from projects.models import Project, ProjectImage

User = get_user_model()
TEMP_MEDIA = tempfile.mkdtemp()


def png(name="photo.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), "blue").save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class DashboardTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.staff = User.objects.create_user("staff", password="pw12345!", is_staff=True)
        self.customer = User.objects.create_user("cust", password="pw12345!")
        self.category = Category.objects.create(name="Water")
        self.client.force_login(self.staff)

    # ---------- access ----------

    def test_anonymous_is_sent_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/?next=/dashboard/", response["Location"])

    def test_customer_gets_403(self):
        self.client.force_login(self.customer)
        for url in (reverse("dashboard:home"), reverse("dashboard:list", args=["products"]),
                    reverse("dashboard:site")):
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_customer_cannot_post(self):
        product = Product.objects.create(category=self.category, name="A", price=10)
        self.client.force_login(self.customer)
        response = self.client.post(reverse("dashboard:delete", args=["products", product.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())

    def test_all_pages_open_for_staff(self):
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:site")).status_code, 200)
        for key in ("announcements", "highlights", "team", "categories", "products", "projects"):
            self.assertEqual(self.client.get(reverse("dashboard:list", args=[key])).status_code, 200, key)
            self.assertEqual(self.client.get(reverse("dashboard:new", args=[key])).status_code, 200, key)

    def test_unknown_section_is_404(self):
        self.assertEqual(self.client.get("/dashboard/nonsense/").status_code, 404)

    # ---------- create / edit ----------

    def test_create_product_and_unique_slug(self):
        data = {"category": self.category.pk, "name": "Mango Drink", "price": "30.00",
                "unit": "bottle", "is_available": "on"}
        r1 = self.client.post(reverse("dashboard:new", args=["products"]), data)
        r2 = self.client.post(reverse("dashboard:new", args=["products"]), data)  # same name again
        self.assertEqual(r1.status_code, 302)
        self.assertEqual(r2.status_code, 302)
        self.assertEqual(sorted(Product.objects.values_list("slug", flat=True)),
                         ["mango-drink", "mango-drink-2"])

    def test_edit_product_keeps_slug(self):
        product = Product.objects.create(category=self.category, name="Water 1L", price=25)
        old_slug = product.slug
        self.client.post(reverse("dashboard:edit", args=["products", product.pk]), {
            "category": self.category.pk, "name": "Water 1 Litre", "price": "26.00", "unit": "bottle"})
        product.refresh_from_db()
        self.assertEqual(product.name, "Water 1 Litre")
        self.assertEqual(product.slug, old_slug)
        self.assertFalse(product.is_available)  # switch left off in the form

    def test_product_requires_price(self):
        response = self.client.post(reverse("dashboard:new", args=["products"]),
                                    {"category": self.category.pk, "name": "No price"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")
        self.assertEqual(Product.objects.count(), 0)

    def test_announcement_datetime_and_validation(self):
        url = reverse("dashboard:new", args=["announcements"])
        ok = self.client.post(url, {"title": "Dashain offer", "message": "10% off",
                                    "show_frequency": "session",
                                    "start_at": "2026-11-05T09:30", "is_active": "on"})
        self.assertEqual(ok.status_code, 302)
        ann = Announcement.objects.get()
        # Typed as Kathmandu time: 09:30 NPT is stored as 03:45 UTC
        self.assertEqual(ann.start_at.strftime("%H:%M"), "03:45")

        bad_link = self.client.post(url, {"title": "x", "message": "y", "button_text": "Go",
                                          "button_url": "javascript:alert(1)",
                                          "start_at": "2026-11-05T09:30"})
        self.assertContains(bad_link, "must start with")

        bad_dates = self.client.post(url, {"title": "x", "message": "y",
                                           "start_at": "2026-11-05T09:30", "end_at": "2026-11-04T09:30"})
        self.assertContains(bad_dates, "end time must be after")
        self.assertEqual(Announcement.objects.count(), 1)

    def test_announcement_edit_form_shows_local_time(self):
        ann = Announcement.objects.create(title="T", message="M")
        response = self.client.get(reverse("dashboard:edit", args=["announcements", ann.pk]))
        self.assertContains(response, 'type="datetime-local"')
        self.assertContains(response, 'name="start_at"')

    def test_highlight_icon_validation(self):
        url = reverse("dashboard:new", args=["highlights"])
        bad = self.client.post(url, {"icon": "star", "title": "T", "order": 1})
        self.assertContains(bad, "Bootstrap icon name")
        good = self.client.post(url, {"icon": "bi-star", "title": "T", "order": 1, "is_active": "on"})
        self.assertEqual(good.status_code, 302)

    def test_team_member_with_photo(self):
        response = self.client.post(reverse("dashboard:new", args=["team"]),
                                    {"name": "Sita", "position": "Manager", "order": 1,
                                     "photo": png("sita.png"), "is_active": "on"})
        self.assertEqual(response.status_code, 302)
        member = TeamMember.objects.get()
        self.assertTrue(member.photo.name.startswith("team/"))
        listing = self.client.get(reverse("dashboard:list", args=["team"]))
        self.assertContains(listing, member.photo.url)
        edit = self.client.get(reverse("dashboard:edit", args=["team", member.pk]))
        self.assertContains(edit, 'class="form-preview"')

    def test_non_image_upload_rejected(self):
        fake = SimpleUploadedFile("evil.png", b"not an image", content_type="image/png")
        response = self.client.post(reverse("dashboard:new", args=["team"]),
                                    {"name": "X", "position": "Y", "order": 1, "photo": fake})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TeamMember.objects.count(), 0)

    def test_image_size_limit(self):
        with mock.patch("dashboard.forms.MAX_IMAGE_MB", 0.00001):
            response = self.client.post(reverse("dashboard:new", args=["team"]),
                                        {"name": "X", "position": "Y", "order": 1, "photo": png()})
        self.assertContains(response, "too large")
        self.assertEqual(TeamMember.objects.count(), 0)

    # ---------- toggle ----------

    def test_toggle_shows_and_hides(self):
        product = Product.objects.create(category=self.category, name="P", price=1)
        url = reverse("dashboard:toggle", args=["products", product.pk])
        self.client.post(url, {"next": "/dashboard/products/?page=1"})
        product.refresh_from_db()
        self.assertFalse(product.is_available)
        response = self.client.post(url)
        product.refresh_from_db()
        self.assertTrue(product.is_available)
        self.assertEqual(response["Location"], "/dashboard/products/")

    def test_toggle_rejects_external_redirect(self):
        product = Product.objects.create(category=self.category, name="P", price=1)
        response = self.client.post(reverse("dashboard:toggle", args=["products", product.pk]),
                                    {"next": "https://evil.example/"})
        self.assertEqual(response["Location"], "/dashboard/products/")

    def test_toggle_needs_post_and_a_toggle_field(self):
        product = Product.objects.create(category=self.category, name="P", price=1)
        self.assertEqual(self.client.get(reverse("dashboard:toggle", args=["products", product.pk])).status_code, 405)
        self.assertEqual(self.client.post(reverse("dashboard:toggle", args=["categories", self.category.pk])).status_code, 404)

    # ---------- delete ----------

    def test_delete_needs_confirmation_then_deletes(self):
        member = TeamMember.objects.create(name="A", position="B")
        url = reverse("dashboard:delete", args=["team", member.pk])
        self.assertContains(self.client.get(url), "Delete team member?")
        self.assertTrue(TeamMember.objects.exists())
        self.client.post(url)
        self.assertFalse(TeamMember.objects.exists())

    def test_cannot_delete_ordered_product_or_used_category(self):
        product = Product.objects.create(category=self.category, name="P", price=5)
        order = Order.objects.create(customer=self.customer, full_name="C", phone="1", address="A")
        OrderItem.objects.create(order=order, product=product, quantity=1, unit_price=5)

        r = self.client.post(reverse("dashboard:delete", args=["products", product.pk]), follow=True)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())
        self.assertContains(r, "cannot be deleted")

        r = self.client.post(reverse("dashboard:delete", args=["categories", self.category.pk]), follow=True)
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())
        self.assertContains(r, "cannot be deleted")

    # ---------- site content ----------

    def test_site_content_save_and_error_tab(self):
        url = reverse("dashboard:site")
        ok = self.client.post(url, {"company_name": "Mountain Beverage Group", "tagline": "Save Water",
                                    "about_text": "About us", "email": "info@example.com"})
        self.assertEqual(ok.status_code, 302)
        site = SiteSettings.load()
        self.assertEqual(site.tagline, "Save Water")
        self.assertEqual(site.about_text, "About us")

        bad = self.client.post(url, {"company_name": "X", "email": "not-an-email"})
        self.assertEqual(bad.status_code, 200)
        self.assertContains(bad, "Enter a valid email")
        self.assertEqual(bad.context["active_tab"], "tab2")  # the Contact tab opens
        self.assertEqual(SiteSettings.objects.count(), 1)

    # ---------- projects and gallery ----------

    def test_project_gallery_flow(self):
        response = self.client.post(reverse("dashboard:new", args=["projects"]), {
            "title": "Event", "description": "D", "date": "2026-05-12", "is_published": "on"})
        project = Project.objects.get()
        self.assertEqual(project.date, date(2026, 5, 12))
        self.assertRedirects(response, reverse("dashboard:edit", args=["projects", project.pk]))

        add_url = reverse("dashboard:gallery_add", args=[project.pk])
        bad = SimpleUploadedFile("a.png", b"nope", content_type="image/png")
        self.client.post(add_url, {"images": [png("one.png"), png("two.png"), bad]})
        self.assertEqual(project.images.count(), 2)

        edit = self.client.get(reverse("dashboard:edit", args=["projects", project.pk]))
        self.assertEqual(len(edit.context["gallery"]), 2)

        image = project.images.first()
        stored_path = image.image.path
        self.client.post(reverse("dashboard:gallery_delete", args=[project.pk, image.pk]))
        self.assertEqual(project.images.count(), 1)
        self.assertFalse(os.path.exists(stored_path))

    def test_gallery_add_without_files(self):
        project = Project.objects.create(title="P", description="D", date=date(2026, 1, 1))
        response = self.client.post(reverse("dashboard:gallery_add", args=[project.pk]), follow=True)
        self.assertContains(response, "Choose at least one photo")

    def test_gallery_delete_wrong_project_is_404(self):
        p1 = Project.objects.create(title="P1", description="D", date=date(2026, 1, 1))
        p2 = Project.objects.create(title="P2", description="D", date=date(2026, 1, 1))
        image = ProjectImage.objects.create(project=p1, image=png())
        response = self.client.post(reverse("dashboard:gallery_delete", args=[p2.pk, image.pk]))
        self.assertEqual(response.status_code, 404)

    # ---------- list features ----------

    def test_search_and_pagination(self):
        for i in range(20):
            Product.objects.create(category=self.category, name=f"Item {i:02d}", price=1)
        url = reverse("dashboard:list", args=["products"])
        self.assertEqual(len(self.client.get(url).context["rows"]), 15)
        self.assertEqual(len(self.client.get(url, {"page": 2}).context["rows"]), 5)
        self.assertEqual(len(self.client.get(url, {"q": "Item 07"}).context["rows"]), 1)

    def test_list_shows_zero_values(self):
        Highlight.objects.create(title="H", order=0)
        response = self.client.get(reverse("dashboard:list", args=["highlights"]))
        self.assertRegex(response.content.decode(), r"<td>\s*0\s*</td>")

    def test_home_counts(self):
        Product.objects.create(category=self.category, name="P", price=1)
        response = self.client.get(reverse("dashboard:home"))
        counts = {c["label"]: c["count"] for c in response.context["content_cards"]}
        self.assertEqual(counts["Products"], 1)