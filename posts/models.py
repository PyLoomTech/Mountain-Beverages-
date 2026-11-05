from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import Truncator

from core.utils import clean_html, plain_text, unique_slug


class PostQuerySet(models.QuerySet):
    def live(self):
        """Posts visitors can see: published, and their publish time has arrived."""
        return self.filter(is_published=True, published_at__lte=timezone.now())


class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    summary = models.CharField(
        max_length=300, blank=True,
        help_text="Short text for the news list and search results. If empty, the start of the post is used.",
    )
    cover_image = models.ImageField(upload_to="posts/", blank=True)
    content = models.TextField()
    is_published = models.BooleanField(
        default=False, help_text="Turn off to keep it as a draft that visitors cannot see."
    )
    published_at = models.DateTimeField(
        default=timezone.now,
        help_text="The date shown on the post. Set a future time to schedule it.",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name="posts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at", "-id"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.title)
        # Whatever way a post is saved (dashboard, admin, shell), the HTML is made safe
        self.content = clean_html(self.content)
        super().save(*args, **kwargs)

    @property
    def is_live(self):
        return self.is_published and self.published_at <= timezone.now()

    @property
    def excerpt(self):
        """Text for cards: the summary, or the first words of the post."""
        return self.summary or Truncator(plain_text(self.content)).words(30)

    def __str__(self):
        return self.title