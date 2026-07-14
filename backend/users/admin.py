from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from users.contact_group import ContactGroup
from users.models import User
from users.roles import PROTECTED_ROLE_NAMES, Role


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("phone_number", "display_name", "is_staff", "created_at")
    list_filter = ("is_staff", "is_superuser", "is_active", "is_paused")
    search_fields = ("phone_number", "display_name", "email")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("Personal info", {"fields": ("display_name", "email")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_paused",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone_number", "display_name", "password1", "password2"),
            },
        ),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "is_default", "permission_count")
    readonly_fields = ("id",)

    def permission_count(self, obj):
        return len(obj.permissions)

    setattr(permission_count, "short_description", "Permissions")

    def has_delete_permission(self, request, obj=None):
        if obj and obj.name in PROTECTED_ROLE_NAMES:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(ContactGroup)
class ContactGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    search_fields = ("name", "owner__phone_number", "owner__display_name")
    raw_id_fields = ("owner",)
    filter_horizontal = ("members",)
    readonly_fields = ("id", "created_at", "updated_at")
