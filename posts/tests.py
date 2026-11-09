from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Announcement
from dashboard.testing import en
from posts.models import Post

User = get_user_model()

DIRTY = (
    '<h1>Big title</h1><div>Hello <strong>world</strong> '
    '<a href="https://example.com" onclick="steal()">link</a>'
    '<script>alert(1)</script><img src="x" onerror="alert(2)">'
    '<a href="javascript:alert(3)">bad link</a>'
    '<iframe src="https://evil.example"></iframe></div>'
)


def make_post(title="Post", live=True, **extra):
    when = timezone.now() - timedelta(hours=1) if live else timezone.now() + timedelta(days=2)
    return Post.objects.create(title=title, content="<div>Body</div>", is_published=True,
                               published_at=extra.pop("published_at", when), **extra)


class PostModelTests(TestCase):
    def test_content_is_cleaned_on_save(self):
        post = Post.objects.create(title="T", content=DIRTY)
        html = post.content
        self.assertIn("<strong>world</strong>", html)
        self.assertIn('href="https://example.com"', html)
        self.assertIn('rel="noopener noreferrer"', html)
        self.assertIn("<h2>Big title</h2>", html)  # h1 becomes h2
        for forbidden in ("<script", "alert(1)", "onclick", "<img", "onerror", "javascript:", "<iframe", "<h1"):
            self.assertNotIn(forbidden, html)

    def test_cleaning_also_happens_on_update(self):
        post = Post.objects.create(title="T", content="<div>ok</div>")
        post.content = '<div onmouseover="x()">changed</div>'
        post.save()
        post.refresh_from_db()
        self.assertNotIn("onmouseover", post.content)

    def test_unique_slugs(self):
        a = Post.objects.create(title="Same title", content="x")
        b = Post.objects.create(title="Same title", content="x")
        self.assertEqual((a.slug, b.slug), ("same-title", "same-title-2"))

    def test_live_queryset(self):
        published = make_post("Published")
        make_post("Scheduled", live=False)
        Post.objects.create(title="Draft", content="x", is_published=False)
        self.assertEqual(list(Post.objects.live()), [published])

    def test_excerpt(self):
        with_summary = Post.objects.create(title="A", summary="My summary", content="<div>Long body</div>")
        self.assertEqual(with_summary.excerpt, "My summary")
        body = " ".join(["word"] * 60)
        no_summary = Post.objects.create(title="B", content=f"<div>Fish &amp; chips {body}</div>")
        self.assertTrue(no_summary.excerpt.startswith("Fish & chips"))  # no double escaping
        self.assertLess(len(no_summary.excerpt.split()), 35)

    def test_is_live(self):
        self.assertTrue(make_post("a").is_live)
        self.assertFalse(make_post("b", live=False).is_live)
        self.assertFalse(Post.objects.create(title="c", content="x").is_live)


class PublicPostTests(TestCase):
    def test_list_shows_only_live_posts(self):
        make_post("Visible post")
        make_post("Future post", live=False)
        Post.objects.create(title="Draft post", content="x")
        response = self.client.get(reverse("post_list"))
        self.assertContains(response, "Visible post")
        self.assertNotContains(response, "Future post")
        self.assertNotContains(response, "Draft post")

    def test_list_empty_message(self):
        self.assertContains(self.client.get(reverse("post_list")), "No news has been published yet")

    def test_list_is_paginated(self):
        for i in range(11):
            make_post(f"News {i}", published_at=timezone.now() - timedelta(hours=i + 1))
        first = self.client.get(reverse("post_list"))
        self.assertEqual(len(first.context["page_obj"]), 9)
        second = self.client.get(reverse("post_list"), {"page": 2})
        self.assertEqual(len(second.context["page_obj"]), 2)

    def test_detail_shows_clean_content(self):
        post = Post.objects.create(title="Clean me", content=DIRTY, is_published=True,
                                   published_at=timezone.now() - timedelta(minutes=1), summary="Short text")
        response = self.client.get(reverse("post_detail", args=[post.slug]))
        self.assertContains(response, "Clean me")
        self.assertContains(response, "<strong>world</strong>", html=False)
        self.assertNotContains(response, "alert(1)")
        self.assertNotContains(response, "onclick")
        self.assertContains(response, '<meta name="description" content="Short text">', html=False)

    def test_draft_and_scheduled_posts_are_404(self):
        draft = Post.objects.create(title="Draft", content="x")
        scheduled = make_post("Soon", live=False)
        self.assertEqual(self.client.get(reverse("post_detail", args=[draft.slug])).status_code, 404)
        self.assertEqual(self.client.get(reverse("post_detail", args=[scheduled.slug])).status_code, 404)
        self.assertEqual(self.client.get(reverse("post_detail", args=["does-not-exist"])).status_code, 404)

    def test_scheduled_post_goes_live_when_time_arrives(self):
        post = make_post("Timed", live=False)
        Post.objects.filter(pk=post.pk).update(published_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.client.get(reverse("post_detail", args=[post.slug])).status_code, 200)

    def test_home_page_latest_news(self):
        self.assertNotContains(self.client.get(reverse("home")), "Latest News")  # none yet: no empty heading
        make_post("Fresh news")
        make_post("Hidden future", live=False)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Latest News")
        self.assertContains(response, "Fresh news")
        self.assertNotContains(response, "Hidden future")

    def test_navbar_links_to_news(self):
        self.assertContains(self.client.get(reverse("home")), reverse("post_list"))


class DashboardPostTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("editor", password="pw12345!", is_staff=True)
        self.client.force_login(self.staff)

    def test_new_post_form_has_editor(self):
        response = self.client.get(reverse("dashboard:new", args=["posts"]))
        self.assertContains(response, "<trix-editor")
        self.assertContains(response, 'type="hidden" name="content_en"')
        self.assertContains(response, 'type="hidden" name="content_ne"')

    def test_create_post_sets_author_cleans_html_and_defaults_to_draft(self):
        response = self.client.post(reverse("dashboard:new", args=["posts"]), en(Post, {
            "title": "Our new plant", "content": DIRTY,
            "published_at": "2026-11-10T10:00",
        }))
        self.assertEqual(response.status_code, 302)
        post = Post.objects.get()
        self.assertEqual(post.author, self.staff)
        self.assertFalse(post.is_published)  # switch was off
        self.assertNotIn("<script", post.content)
        self.assertNotIn("onclick", post.content)
        self.assertEqual(self.client.get(reverse("post_detail", args=[post.slug])).status_code, 404)

    def test_publish_and_unpublish_with_toggle(self):
        post = Post.objects.create(title="Toggle me", content="<div>x</div>",
                                   published_at=timezone.now() - timedelta(minutes=5))
        toggle = reverse("dashboard:toggle", args=["posts", post.pk])
        self.client.post(toggle)
        self.assertEqual(self.client.get(reverse("post_detail", args=[post.slug])).status_code, 200)
        self.client.post(toggle)
        self.assertEqual(self.client.get(reverse("post_detail", args=[post.slug])).status_code, 404)

    def test_editing_keeps_original_author(self):
        other = User.objects.create_user("other", password="pw12345!", is_staff=True)
        post = Post.objects.create(title="Mine", content="<div>x</div>", author=other)
        self.client.post(reverse("dashboard:edit", args=["posts", post.pk]), en(Post, {
            "title": "Mine edited", "content": "<div>y</div>", "published_at": "2026-11-10T10:00"}))
        post.refresh_from_db()
        self.assertEqual(post.title, "Mine edited")
        self.assertEqual(post.author, other)

    def test_edit_form_shows_existing_content_in_editor(self):
        post = Post.objects.create(title="Edit", content="<div>Existing <strong>text</strong></div>")
        response = self.client.get(reverse("dashboard:edit", args=["posts", post.pk]))
        self.assertContains(response, "Existing &lt;strong&gt;text&lt;/strong&gt;")  # escaped inside the hidden input

    def test_content_is_required(self):
        response = self.client.post(reverse("dashboard:new", args=["posts"]),
                                    en(Post, {"title": "No body", "content": "", "published_at": "2026-11-10T10:00"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")
        self.assertEqual(Post.objects.count(), 0)

    def test_list_and_search(self):
        Post.objects.create(title="Water quality update", content="x")
        Post.objects.create(title="New office", content="x")
        response = self.client.get(reverse("dashboard:list", args=["posts"]), {"q": "water"})
        self.assertEqual(len(response.context["rows"]), 1)

    def test_customer_cannot_use_posts_dashboard(self):
        customer = User.objects.create_user("cust", password="pw12345!")
        self.client.force_login(customer)
        self.assertEqual(self.client.get(reverse("dashboard:list", args=["posts"])).status_code, 403)


class AnnouncementFrequencyTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("editor", password="pw12345!", is_staff=True)
        self.client.force_login(self.staff)

    def test_default_is_once_per_visit(self):
        self.assertEqual(Announcement.objects.create(title="T", message="M").show_frequency, "session")

    def test_staff_can_choose_frequency(self):
        response = self.client.post(reverse("dashboard:new", args=["announcements"]), en(Announcement, {
            "title": "Offer", "message": "10% off", "show_frequency": "daily",
            "start_at": "2026-01-01T09:00", "is_active": "on"}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Announcement.objects.get().show_frequency, "daily")

    def test_invalid_frequency_rejected(self):
        response = self.client.post(reverse("dashboard:new", args=["announcements"]), en(Announcement, {
            "title": "Offer", "message": "x", "show_frequency": "hourly", "start_at": "2026-01-01T09:00"}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Announcement.objects.count(), 0)

    def test_home_page_passes_frequency_to_the_pop_up(self):
        Announcement.objects.create(title="Live", message="M", show_frequency="always")
        self.assertContains(self.client.get(reverse("home")), 'data-frequency="always"')

    def test_dashboard_list_shows_frequency(self):
        Announcement.objects.create(title="Live", message="M", show_frequency="daily")
        self.assertContains(self.client.get(reverse("dashboard:list", args=["announcements"])), "Once per day")
