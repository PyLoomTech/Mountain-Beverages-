from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "phone", "status", "total_display", "created_at")
    list_filter = ("status", "created_at")
    list_editable = ("status",)
    search_fields = ("full_name", "phone", "customer__username")
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]

    @admin.display(description="Total (NPR)")
    def total_display(self, obj):
        return obj.total