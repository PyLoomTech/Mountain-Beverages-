from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import Category, Product
from core.models import ContactMessage
from orders.models import Order, OrderItem
from reviews.models import Review

User = get_user_model()


class OperationsTestCase(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("staff", password="pw12345!", is_staff=True)
        self.customer = User.objects.create_user(
            "sita", password="pw12345!", first_name="Sita", last_name="Sharma",
            phone="9800000002", email="sita@example.com")
        self.category = Category.objects.create(name="Water")
        self.product = Product.objects.create(category=self.category, name="Jar", price=150)
        self.client.force_login(self.staff)

    def make_order(self, status="pending", customer=None, name="Sita Sharma", qty=2):
        order = Order.objects.create(customer=customer or self.customer, status=status,
                                     full_name=name, phone="9800000002", address="Tole 1")
        OrderItem.objects.create(order=order, product=self.product, quantity=qty, unit_price=150)
        return order


class AccessTests(OperationsTestCase):
    URLS = ("dashboard:orders", "dashboard:reviews", "dashboard:inbox", "dashboard:customers")

    def test_customer_gets_403_everywhere(self):
        order, review = self.make_order(), Review.objects.create(customer=self.customer, comment="x")
        contact = ContactMessage.objects.create(name="A", email="a@example.com", message="m")
        self.client.force_login(self.customer)
        for name in self.URLS:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)
        for name, pk in (("dashboard:order_detail", order.pk), ("dashboard:message_detail", contact.pk),
                         ("dashboard:customer_detail", self.customer.pk)):
            self.assertEqual(self.client.get(reverse(name, args=[pk])).status_code, 403, name)
        posts = (("dashboard:order_status", order.pk), ("dashboard:review_status", review.pk),
                 ("dashboard:message_unread", contact.pk), ("dashboard:customer_active", self.customer.pk))
        for name, pk in posts:
            self.assertEqual(self.client.post(reverse(name, args=[pk]), {"status": "approved"}).status_code, 403, name)
        order.refresh_from_db()
        self.assertEqual(order.status, "pending")

    def test_anonymous_is_sent_to_login(self):
        self.client.logout()
        for name in self.URLS:
            self.assertEqual(self.client.get(reverse(name)).status_code, 302, name)

    def test_pages_open_for_staff(self):
        for name in self.URLS:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)


class OrderTests(OperationsTestCase):
    def test_list_filter_tabs_and_counts(self):
        self.make_order("pending")
        self.make_order("pending")
        self.make_order("delivered")
        response = self.client.get(reverse("dashboard:orders"))
        counts = {tab["label"]: tab["count"] for tab in response.context["tabs"]}
        self.assertEqual(counts, {"All": 3, "Pending": 2, "Confirmed": 0, "Delivered": 1, "Cancelled": 0})
        pending = self.client.get(reverse("dashboard:orders"), {"status": "pending"})
        self.assertEqual(len(pending.context["page_obj"]), 2)
        junk = self.client.get(reverse("dashboard:orders"), {"status": "hacked"})
        self.assertEqual(len(junk.context["page_obj"]), 3)  # invalid value is ignored

    def test_search_by_name_phone_username_and_number(self):
        a = self.make_order(name="Ram Thapa")
        b = self.make_order(name="Hari Rai")
        url = reverse("dashboard:orders")
        self.assertEqual([o.pk for o in self.client.get(url, {"q": "ram"}).context["page_obj"]], [a.pk])
        self.assertEqual(len(self.client.get(url, {"q": "9800000002"}).context["page_obj"]), 2)
        self.assertEqual(len(self.client.get(url, {"q": "sita"}).context["page_obj"]), 2)  # username
        self.assertEqual([o.pk for o in self.client.get(url, {"q": f"#{b.pk}"}).context["page_obj"]], [b.pk])

    def test_detail_shows_items_total_and_delivery(self):
        order = self.make_order(qty=3)
        response = self.client.get(reverse("dashboard:order_detail", args=[order.pk]))
        self.assertContains(response, "Jar")
        self.assertContains(response, "450.00")  # 3 x 150
        self.assertContains(response, "Tole 1")

    def test_change_status(self):
        order = self.make_order()
        url = reverse("dashboard:order_status", args=[order.pk])
        response = self.client.post(url, {"status": "confirmed"})
        order.refresh_from_db()
        self.assertEqual(order.status, "confirmed")
        self.assertRedirects(response, reverse("dashboard:order_detail", args=[order.pk]))
        self.client.post(url, {"status": "delivered", "next": "/dashboard/orders/?status=confirmed"})
        order.refresh_from_db()
        self.assertEqual(order.status, "delivered")

    def test_invalid_status_and_external_redirect_are_refused(self):
        order = self.make_order()
        url = reverse("dashboard:order_status", args=[order.pk])
        self.client.post(url, {"status": "shipped-to-moon"})
        order.refresh_from_db()
        self.assertEqual(order.status, "pending")
        response = self.client.post(url, {"status": "confirmed", "next": "https://evil.example/"})
        self.assertEqual(response["Location"], reverse("dashboard:order_detail", args=[order.pk]))

    def test_status_needs_post(self):
        order = self.make_order()
        self.assertEqual(self.client.get(reverse("dashboard:order_status", args=[order.pk])).status_code, 405)

    def test_delivered_order_lets_the_customer_review(self):
        order = self.make_order()
        self.client.post(reverse("dashboard:order_status", args=[order.pk]), {"status": "delivered"})
        self.assertTrue(Order.objects.filter(customer=self.customer, status="delivered").exists())

    def test_order_by_staff_user_does_not_break_the_page(self):
        order = self.make_order(customer=self.staff)  # e.g. the owner testing checkout
        self.assertEqual(self.client.get(reverse("dashboard:order_detail", args=[order.pk])).status_code, 200)


class ReviewTests(OperationsTestCase):
    def test_approve_reject_and_reset(self):
        review = Review.objects.create(customer=self.customer, comment="Good water")
        url = reverse("dashboard:review_status", args=[review.pk])
        self.client.post(url, {"status": "approved"})
        review.refresh_from_db()
        self.assertEqual(review.status, "approved")
        self.assertEqual(Review.objects.filter(status="approved").count(), 1)
        self.client.post(url, {"status": "rejected"})
        review.refresh_from_db()
        self.assertEqual(review.status, "rejected")
        self.client.post(url, {"status": "bogus"})
        review.refresh_from_db()
        self.assertEqual(review.status, "rejected")

    def test_tabs_and_search(self):
        other = User.objects.create_user("hari", password="pw12345!", first_name="Hari")
        Review.objects.create(customer=self.customer, comment="Lovely taste", status="approved")
        Review.objects.create(customer=other, comment="Late delivery")
        response = self.client.get(reverse("dashboard:reviews"), {"status": "pending"})
        self.assertEqual([r.customer for r in response.context["page_obj"]], [other])
        found = self.client.get(reverse("dashboard:reviews"), {"q": "taste"})
        self.assertEqual(len(found.context["page_obj"]), 1)

    def test_delete_needs_confirmation(self):
        review = Review.objects.create(customer=self.customer, comment="Spam")
        url = reverse("dashboard:review_delete", args=[review.pk])
        self.assertContains(self.client.get(url), "Delete review?")
        self.assertTrue(Review.objects.exists())
        self.client.post(url)
        self.assertFalse(Review.objects.exists())

    def test_approved_review_appears_on_the_site_only_after_approval(self):
        review = Review.objects.create(customer=self.customer, comment="Excellent service")
        self.assertEqual(Review.objects.filter(status="approved").count(), 0)
        self.client.post(reverse("dashboard:review_status", args=[review.pk]), {"status": "approved"})
        self.assertEqual(Review.objects.filter(status="approved").count(), 1)


class MessageTests(OperationsTestCase):
    def setUp(self):
        super().setUp()
        self.contact = ContactMessage.objects.create(
            name="Bikash", email="bikash@example.com", phone="9811111111", message="Do you deliver to Butwal?")

    def test_opening_marks_as_read_and_unread_button_reverses_it(self):
        self.assertFalse(self.contact.is_read)
        response = self.client.get(reverse("dashboard:message_detail", args=[self.contact.pk]))
        self.assertContains(response, "Do you deliver to Butwal?")
        self.assertContains(response, "mailto:bikash@example.com")
        self.contact.refresh_from_db()
        self.assertTrue(self.contact.is_read)
        self.client.post(reverse("dashboard:message_unread", args=[self.contact.pk]))
        self.contact.refresh_from_db()
        self.assertFalse(self.contact.is_read)

    def test_unread_filter_and_search(self):
        read = ContactMessage.objects.create(name="Old", email="o@example.com", message="hello", is_read=True)
        unread = self.client.get(reverse("dashboard:inbox"), {"filter": "unread"})
        self.assertEqual([m.pk for m in unread.context["page_obj"]], [self.contact.pk])
        found = self.client.get(reverse("dashboard:inbox"), {"q": "butwal"})
        self.assertEqual([m.pk for m in found.context["page_obj"]], [self.contact.pk])
        self.assertEqual((unread.context["total"], unread.context["unread"]), (2, 1))
        self.assertTrue(read.is_read)

    def test_delete(self):
        url = reverse("dashboard:message_delete", args=[self.contact.pk])
        self.assertContains(self.client.get(url), "Delete message?")
        self.client.post(url)
        self.assertFalse(ContactMessage.objects.exists())


class CustomerTests(OperationsTestCase):
    def test_list_counts_orders_and_hides_staff(self):
        self.make_order()
        self.make_order()
        response = self.client.get(reverse("dashboard:customers"))
        customers = list(response.context["page_obj"])
        self.assertEqual([c.username for c in customers], ["sita"])  # staff are not listed
        self.assertEqual(customers[0].order_count, 2)

    def test_search(self):
        User.objects.create_user("hari", password="pw12345!", first_name="Hari", phone="9822222222")
        url = reverse("dashboard:customers")
        self.assertEqual(len(self.client.get(url, {"q": "9822"}).context["page_obj"]), 1)
        self.assertEqual(len(self.client.get(url, {"q": "sharma"}).context["page_obj"]), 1)

    def test_detail_shows_orders_and_review(self):
        self.make_order()
        Review.objects.create(customer=self.customer, comment="Great", status="approved")
        response = self.client.get(reverse("dashboard:customer_detail", args=[self.customer.pk]))
        self.assertContains(response, "sita@example.com")
        self.assertContains(response, "Orders (1)")
        self.assertContains(response, "Great")

    def test_staff_account_is_not_a_customer_page(self):
        self.assertEqual(self.client.get(reverse("dashboard:customer_detail", args=[self.staff.pk])).status_code, 404)

    def test_block_and_unblock_stops_login(self):
        url = reverse("dashboard:customer_active", args=[self.customer.pk])
        self.client.post(url)
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_active)
        other = self.client_class()
        self.assertFalse(other.login(username="sita", password="pw12345!"))
        self.client.post(url)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_active)
        self.assertTrue(other.login(username="sita", password="pw12345!"))

    def test_cannot_block_staff_via_url(self):
        self.assertEqual(self.client.post(reverse("dashboard:customer_active", args=[self.staff.pk])).status_code, 404)
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)


class OverviewAndSidebarTests(OperationsTestCase):
    def test_sidebar_badges_and_overview_cards(self):
        self.make_order("pending")
        Review.objects.create(customer=self.customer, comment="x")
        ContactMessage.objects.create(name="A", email="a@example.com", message="m")
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.context["badges"], {"orders": 1, "reviews": 1, "inbox": 1})
        urls = [card["url"] for card in response.context["work_cards"]]
        self.assertEqual(urls, [
            reverse("dashboard:orders") + "?status=pending",
            reverse("dashboard:reviews") + "?status=pending",
            reverse("dashboard:inbox") + "?filter=unread",
        ])
        self.assertContains(response, reverse("dashboard:customers"))
