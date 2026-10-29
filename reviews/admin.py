from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("customer", "rating", "short_comment", "status", "created_at")
    list_filter = ("status", "rating")
    list_editable = ("status",)
    search_fields = ("comment", "customer__username")
    actions = ["approve_reviews", "reject_reviews"]

    @admin.display(description="Comment")
    def short_comment(self, obj):
        return obj.comment[:60]

    @admin.action(description="Approve selected reviews")
    def approve_reviews(self, request, queryset):
        queryset.update(status="approved")

    @admin.action(description="Reject selected reviews")
    def reject_reviews(self, request, queryset):
        queryset.update(status="rejected")