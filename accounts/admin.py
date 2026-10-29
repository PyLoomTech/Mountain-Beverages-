from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Extra information", {"fields": ("role", "phone", "address")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Extra information", {"fields": ("role", "phone", "address")}),
    )
    list_display = ("username", "email", "phone", "role", "is_staff")
    list_filter = ("role", "is_staff")