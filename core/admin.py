from django.contrib import admin

from .models import Announcement, ContactMessage, Highlight, SiteSettings, TeamMember

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


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "start_at", "end_at", "live_now")
    list_filter = ("is_active",)
    list_editable = ("is_active",)
    search_fields = ("title", "message")
    fieldsets = (
        ("Content", {"fields": ("title", "message", "image")}),
        ("Button (optional)", {"fields": ("button_text", "button_url")}),
        ("When to show", {"fields": ("is_active", "start_at", "end_at")}),
    )

    @admin.display(boolean=True, description="Live now")
    def live_now(self, obj):
        return obj.is_live


@admin.register(Highlight)
class HighlightAdmin(admin.ModelAdmin):
    list_display = ("title", "value", "icon", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "position", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("name", "position")