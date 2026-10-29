from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    image = models.ImageField(upload_to="products/", blank=True)
    short_description = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    specifications = models.TextField(
        blank=True, help_text="One specification per line, e.g. Volume: 1 L"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(
        max_length=30, default="bottle", help_text="e.g. bottle, carton, pack"
    )
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def spec_list(self):
        """Specifications as a list, one item per line (used in templates)."""
        return [line.strip() for line in self.specifications.splitlines() if line.strip()]

    def __str__(self):
        return self.name