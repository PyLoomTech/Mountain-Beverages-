from django.contrib import admin

from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "published_at", "author")
    list_filter = ("is_published",)
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("author",)

    def save_model(self, request, obj, form, change):
        if obj.author_id is None:
            obj.author = request.user
        super().save_model(request, obj, form, change)
