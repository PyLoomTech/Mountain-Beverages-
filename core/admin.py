from django.contrib import admin

from .models import ContactMessage, SiteSettings

# Branding for the admin panel
admin.site.site_header = "Mountain Beverages Admin"
admin.site.site_title = "Mountain Beverages"
admin.site.index_title = "Dashboard"


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Allow adding only if no settings row exists yet
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "is_read", "created_at")
    list_filter = ("is_read",)
    list_editable = ("is_read",)
    search_fields = ("name", "email", "message")