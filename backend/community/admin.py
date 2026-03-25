from community.models import Event, JoinRequest
from django.contrib import admin


@admin.register(JoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "pronouns", "submitted_at")
    list_filter = ("submitted_at",)
    search_fields = ("name", "email")
    ordering = ("-submitted_at",)
    readonly_fields = ("id", "submitted_at")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "start_datetime", "end_datetime", "location")
    list_filter = ("start_datetime",)
    search_fields = ("title", "description", "location")
    ordering = ("start_datetime",)
    readonly_fields = ("id", "created_at")
