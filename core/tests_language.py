from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone, translation

from catalog.models import Category, Product
from core.models import SiteSettings
from dashboard.forms import build_form_class
from dashboard.registry import SECTIONS
from dashboard.testing import en
from posts.models import Post

User = get_user_model()

DIRTY = '<div>Hello <strong>ok</strong><script>alert(1)</script><a href="javascript:x()" onclick="y()">bad</a></div>'


class LanguageTestCase(TestCase):
    """A request to /ne/ leaves Nepali active in the test process, so every test starts in English."""

    def setUp(self):
        super().setUp()
        translation.activate("en")
        self.addCleanup(translation.deactivate)


def live_post(**fields):
    return Post.objects.create(is_published=True, published_at=timezone.now() - timedelta(hours=1), **fields)


class LanguageUrlTests(LanguageTestCase):
    def test_root_redirects_to_the_default_language(self):
        response = self.client.get("/")
        self.assertRedirects(response, "/en/", fetch_redirect_response=False)

    def test_root_follows_the_browser_language(self):
        response = self.client.get("/", HTTP_ACCEPT_LANGUAGE="ne")
        self.assertRedirects(response, "/ne/", fetch_redirect_response=False)

    def test_both_languages_open(self):
        self.assertEqual(self.client.get("/en/").status_code, 200)
        self.assertEqual(self.client.get("/ne/").status_code, 200)

    def test_old_addresses_without_a_language_still_work(self):
        self.assertRedirects(self.client.get("/news/"), "/en/news/", fetch_redirect_response=False)

    def test_url_names_follow_the_active_language(self):
        with translation.override("ne"):
            self.assertEqual(reverse("post_list"), "/ne/news/")
        with translation.override("en"):
            self.assertEqual(reverse("post_list"), "/en/news/")

    def test_staff_panel_addresses_have_no_language_prefix(self):
        self.assertEqual(reverse("dashboard:home"), "/dashboard/")


class ContentInTwoLanguagesTests(LanguageTestCase):
    def test_visitors_see_the_nepali_text_when_it_exists(self):
        live_post(title_en="New plant", title_ne="नयाँ प्लान्ट", content_en="<div>x</div>")
        self.assertContains(self.client.get("/ne/news/"), "नयाँ प्लान्ट")
        self.assertNotContains(self.client.get("/ne/news/"), "New plant")
        self.assertContains(self.client.get("/en/news/"), "New plant")
        self.assertNotContains(self.client.get("/en/news/"), "नयाँ प्लान्ट")

    def test_empty_nepali_falls_back_to_english(self):
        live_post(title_en="Only English", content_en="<div>x</div>")
        self.assertContains(self.client.get("/ne/news/"), "Only English")

    def test_site_text_follows_the_language(self):
        site = SiteSettings.load()
        site.tagline_en, site.tagline_ne = "Save Water Save Life", "पानी जोगाऔं, जीवन बचाऔं"
        site.save()
        self.assertContains(self.client.get("/en/"), "Save Water Save Life")
        self.assertContains(self.client.get("/ne/"), "पानी जोगाऔं, जीवन बचाऔं")

    def test_model_attribute_returns_the_active_language(self):
        category = Category.objects.create(name_en="Water", name_ne="पानी")
        with translation.override("ne"):
            self.assertEqual(Category.objects.get(pk=category.pk).name, "पानी")
        with translation.override("en"):
            self.assertEqual(Category.objects.get(pk=category.pk).name, "Water")

    def test_plain_creation_stores_the_default_language(self):
        product = Product.objects.create(category=Category.objects.create(name="Water"), name="Jar", price=1)
        product.refresh_from_db()
        self.assertEqual(product.name_en, "Jar")
        self.assertIsNone(product.name_ne)


class SafeHtmlInEveryLanguageTests(LanguageTestCase):
    def test_both_languages_are_cleaned_when_saved(self):
        post = Post.objects.create(title_en="T", content_en=DIRTY, content_ne=DIRTY)
        post.refresh_from_db()
        for html in (post.content_en, post.content_ne):
            self.assertIn("<strong>ok</strong>", html)
            for bad in ("<script", "alert(1)", "javascript:", "onclick"):
                self.assertNotIn(bad, html)

    def test_nepali_page_never_shows_unclean_html(self):
        live_post(title_en="T", content_en="<div>x</div>", content_ne=DIRTY)
        with translation.override("ne"):
            response = self.client.get(reverse("post_detail", args=["t"]))
        self.assertContains(response, "<strong>ok</strong>", html=False)
        self.assertNotContains(response, "alert(1)")


class DashboardTwoLanguageTests(LanguageTestCase):
    def setUp(self):
        super().setUp()
        self.staff = User.objects.create_user("editor", password="pw12345!", is_staff=True)
        self.client.force_login(self.staff)

    def test_form_has_general_english_and_nepali_tabs(self):
        response = self.client.get(reverse("dashboard:new", args=["posts"]))
        self.assertEqual([t["title"] for t in response.context["tabs"]], ["General", "English", "नेपाली"])
        self.assertContains(response, "Anything left empty is shown to visitors in English")
        self.assertNotContains(response, "[en]")
        self.assertNotContains(response, "[ne]")

    def test_english_is_required_and_nepali_is_optional(self):
        section = SECTIONS["posts"]
        form = build_form_class(Post, section.fields, section.rich_fields)()
        self.assertTrue(form.fields["title_en"].required)
        self.assertTrue(form.fields["content_en"].required)
        self.assertFalse(form.fields["title_ne"].required)
        self.assertFalse(form.fields["content_ne"].required)

    def test_saving_with_only_english_works(self):
        response = self.client.post(reverse("dashboard:new", args=["posts"]), {
            "title_en": "English only", "content_en": "<div>Body</div>", "published_at": "2026-11-10T10:00"})
        self.assertEqual(response.status_code, 302)
        post = Post.objects.get()
        self.assertEqual(post.title_en, "English only")
        self.assertFalse(post.title_ne)

    def test_missing_english_is_refused_and_its_tab_is_flagged(self):
        response = self.client.post(reverse("dashboard:new", args=["posts"]), {
            "title_ne": "नेपाली मात्र", "content_ne": "<div>x</div>", "published_at": "2026-11-10T10:00"})
        self.assertEqual(response.status_code, 200)
        flagged = [t["id"] for t in response.context["tabs"] if t["has_errors"]]
        self.assertEqual(flagged, ["tab-en"])
        self.assertEqual(Post.objects.count(), 0)

    def test_both_languages_are_saved_and_cleaned(self):
        self.client.post(reverse("dashboard:new", args=["posts"]), {
            "title_en": "Plant", "title_ne": "प्लान्ट", "content_en": DIRTY, "content_ne": DIRTY,
            "published_at": "2026-11-10T10:00"})
        post = Post.objects.get()
        self.assertEqual(post.title_ne, "प्लान्ट")
        self.assertNotIn("<script", post.content_en)
        self.assertNotIn("<script", post.content_ne)

    def test_editing_shows_both_languages(self):
        post = Post.objects.create(title_en="Plant", title_ne="प्लान्ट", content_en="<div>x</div>")
        response = self.client.get(reverse("dashboard:edit", args=["posts", post.pk]))
        self.assertContains(response, 'value="Plant"')
        self.assertContains(response, 'value="प्लान्ट"')

    def test_panel_stays_english_even_if_the_browser_is_nepali(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "ne"
        response = self.client.get(reverse("dashboard:list", args=["products"]), HTTP_ACCEPT_LANGUAGE="ne")
        self.assertEqual(response.context["LANGUAGE_CODE"], "en")

    def test_web_address_comes_from_the_english_name_even_in_a_nepali_browser(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "ne"
        category = Category.objects.create(name="Water")
        self.client.post(reverse("dashboard:new", args=["products"]), {
            "category": category.pk, "name_en": "Mango Drink", "name_ne": "आमको जुस",
            "price": "30.00", "unit_en": "bottle", "is_available": "on"}, HTTP_ACCEPT_LANGUAGE="ne")
        self.assertEqual(Product.objects.get().slug, "mango-drink")

    def test_site_content_has_language_tabs(self):
        response = self.client.get(reverse("dashboard:site"))
        self.assertEqual([t["title"] for t in response.context["tabs"]], ["General", "English", "नेपाली"])
        self.client.post(reverse("dashboard:site"), {
            "company_name_en": "Mountain Beverage Group", "company_name_ne": "माउन्टेन बेभरेज ग्रुप",
            "tagline_en": "Save Water", "tagline_ne": "पानी जोगाऔं"})
        site = SiteSettings.load()
        self.assertEqual((site.tagline_en, site.tagline_ne), ("Save Water", "पानी जोगाऔं"))

    def test_two_categories_can_both_leave_nepali_empty(self):
        url = reverse("dashboard:new", args=["categories"])
        self.assertEqual(self.client.post(url, {"name_en": "Water", "name_ne": ""}).status_code, 302)
        self.assertEqual(self.client.post(url, {"name_en": "Juice", "name_ne": ""}).status_code, 302)
        self.assertEqual(Category.objects.count(), 2)

    def test_duplicate_english_category_name_is_refused(self):
        url = reverse("dashboard:new", args=["categories"])
        self.client.post(url, {"name_en": "Water", "name_ne": ""})
        response = self.client.post(url, {"name_en": "Water", "name_ne": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertEqual(Category.objects.count(), 1)

    def test_search_in_the_list_uses_english(self):
        Category.objects.create(name_en="Water", name_ne="पानी")
        response = self.client.get(reverse("dashboard:list", args=["categories"]), {"q": "water"})
        self.assertEqual(len(response.context["rows"]), 1)


class SeedNepaliTests(LanguageTestCase):
    def test_fills_empty_nepali_and_never_overwrites_staff_text(self):
        from django.core.management import call_command

        category = Category.objects.create(name_en="Packaged Drinking Water")
        product = Product.objects.create(category=category, name_en="Mango Drink 250 ml", price=30, unit_en="bottle")
        written = Product.objects.create(category=category, name_en="Pure Natural Water 1 L", price=25,
                                         name_ne="मेरो आफ्नै नाम")
        call_command("seed_nepali")

        category.refresh_from_db()
        product.refresh_from_db()
        written.refresh_from_db()
        self.assertEqual(category.name_ne, "प्याकेजिङ गरिएको पिउने पानी")
        self.assertEqual(product.name_ne, "आमको पेय २५० मि.ली.")
        self.assertEqual(product.unit_ne, "बोतल")
        self.assertEqual(written.name_ne, "मेरो आफ्नै नाम")  # staff text is kept
        self.assertEqual(SiteSettings.load().tagline_ne, "पानी बचाऔँ, जीवन बचाऔँ")

        call_command("seed_nepali")  # a second run changes nothing
        product.refresh_from_db()
        self.assertEqual(product.name_ne, "आमको पेय २५० मि.ली.")
