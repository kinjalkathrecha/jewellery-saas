from django.contrib import admin

from .models import Lead, Shop, SubscriptionPlan

admin.site.register(SubscriptionPlan)
admin.site.register(Shop)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "shop_name",
        "email",
        "phone",
        "lead_type",
        "status",
        "source",
        "created_at",
    )
    list_filter = ("lead_type", "status", "source", "created_at")
    search_fields = ("name", "shop_name", "email", "phone")
    list_editable = ("status",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Basic Information", {"fields": ("name", "email", "phone", "shop_name", "message")}),
        (
            "Lead Lifecycle & Acquisition",
            {
                "fields": (
                    "lead_type",
                    "status",
                    "source",
                    "utm_source",
                    "utm_medium",
                    "utm_campaign",
                )
            },
        ),
        ("CRM Notes & Timestamps", {"fields": ("notes", "created_at", "updated_at")}),
    )
