from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class SiteSettings(models.Model):
    """Company information shown across the site. Only one row exists."""

    company_name = models.CharField(max_length=150, default="Mountain Beverages Group")
    tagline = models.CharField(max_length=200, blank=True)

    # Home page hero
    hero_title = models.CharField(max_length=200, blank=True)
    hero_subtitle = models.CharField(max_length=300, blank=True)
    hero_image = models.ImageField(upload_to="site/", blank=True)

    # About page
    about_text = models.TextField(blank=True)
    history = models.TextField(blank=True)
    vision = models.TextField(blank=True)
    mission = models.TextField(blank=True)
    core_values = models.TextField(blank=True, help_text="One value per line")

    # Contact page
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    business_hours = models.CharField(max_length=200, blank=True)
    map_embed_url = models.URLField(max_length=700, blank=True)

    # Social links
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    whatsapp_number = models.CharField(max_length=30, blank=True)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def save(self, *args, **kwargs):
        self.pk = 1  # always the same row
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def value_list(self):
        return [v.strip() for v in self.core_values.splitlines() if v.strip()]

    def __str__(self):
        return self.company_name


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.created_at:%Y-%m-%d}"


# ---------------------------------------------------------------------------
# Home page pop-up
# ---------------------------------------------------------------------------

def validate_link(value):
    """Allow only site paths (/products/) or web links (https://...)."""
    if value.startswith("//") or not value.startswith(("/", "http://", "https://")):
        raise ValidationError(
            "The link must start with /, http:// or https:// (for example /products/)."
        )


class Announcement(models.Model):
    """A pop-up shown on the home page while it is live."""

    title = models.CharField(max_length=120)
    message = models.TextField()
    image = models.ImageField(upload_to="announcements/", blank=True)
    button_text = models.CharField(max_length=50, blank=True, help_text="e.g. Shop now")
    button_url = models.CharField(
        max_length=300, blank=True, validators=[validate_link],
        help_text="Page or link the button opens, e.g. /products/ or https://example.com",
    )
    is_active = models.BooleanField(default=True, help_text="Turn off to hide it at any time.")
    start_at = models.DateTimeField(default=timezone.now, help_text="The pop-up appears from this time.")
    end_at = models.DateTimeField(
        null=True, blank=True, help_text="Leave empty to show it until you turn it off."
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_at"]

    def clean(self):
        if self.end_at and self.end_at <= self.start_at:
            raise ValidationError({"end_at": "The end time must be after the start time."})
        if self.button_url and not self.button_text:
            raise ValidationError({"button_text": "Add the text for the button, or clear the link."})

    @property
    def is_live(self):
        now = timezone.now()
        return self.is_active and self.start_at <= now and (self.end_at is None or self.end_at >= now)

    @classmethod
    def current(cls):
        """The newest announcement that is live right now (or None)."""
        now = timezone.now()
        return (
            cls.objects.filter(is_active=True, start_at__lte=now)
            .filter(Q(end_at__isnull=True) | Q(end_at__gte=now))
            .order_by("-start_at")
            .first()
        )

    def __str__(self):
        return self.title



# Company highlights (home page)

class Highlight(models.Model):
    icon = models.CharField(
        max_length=50, default="bi-droplet-fill",
        validators=[RegexValidator(r"^bi-[a-z0-9-]+$", "Use a Bootstrap icon name such as bi-droplet-fill.")],
        help_text="Icon name from icons.getbootstrap.com, e.g. bi-truck or bi-shield-check",
    )
    value = models.CharField(
        max_length=30, blank=True, help_text="Optional big text, e.g. 100% or 10+ years"
    )
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True)
    order = models.PositiveSmallIntegerField(default=0, help_text="Smaller numbers appear first.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title



# Team members (About page)


class TeamMember(models.Model):
    name = models.CharField(max_length=120)
    position = models.CharField(max_length=120)
    photo = models.ImageField(upload_to="team/", blank=True, help_text="A square photo works best.")
    bio = models.TextField(blank=True)
    facebook_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    order = models.PositiveSmallIntegerField(default=0, help_text="Smaller numbers appear first.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} ({self.position})"