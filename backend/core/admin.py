
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    ApplianceCategory,
    Booking,
    Notification,
    Payment,
    Review,
    Service,
    TechnicianProfile,
    User,
)


class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "phone",
        "role",
        "is_phone_verified",
        "is_active",
    )
    list_filter = BaseUserAdmin.list_filter + (
        "role",
        "is_phone_verified",
    )
    search_fields = ("username", "email", "phone")

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Extra",
            {
                "fields": (
                    "role",
                    "phone",
                    "is_phone_verified",
                    "avatar",
                )
            },
        ),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "Extra",
            {
                "fields": ("role", "phone"),
            },
        ),
    )


@admin.register(ApplianceCategory)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "icon")
    search_fields = ("name",)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "category",
        "name",
        "base_price",
        "is_active",
    )
    list_filter = ("category", "is_active")
    search_fields = ("name",)


@admin.register(TechnicianProfile)
class TechnicianAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "experience_years",
        "approval_status",
        "is_available",
        "rating_avg",
        "rating_count",
    )
    list_filter = ("approval_status", "is_available")
    search_fields = ("user__username", "user__phone")
    filter_horizontal = ("expertise",)
    readonly_fields = ("rating_avg", "rating_count")

    actions = (
        "approve_technicians",
        "reject_technicians",
        "toggle_availability",
    )

    @admin.action(description="Approve selected technicians")
    def approve_technicians(self, request, queryset):
        queryset.update(approval_status="APPROVED")

    @admin.action(description="Reject selected technicians")
    def reject_technicians(self, request, queryset):
        queryset.update(approval_status="REJECTED")

    @admin.action(description="Toggle availability of selected technicians")
    def toggle_availability(self, request, queryset):
        for profile in queryset:
            profile.is_available = not profile.is_available
            profile.save(update_fields=["is_available"])


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "booking_id",
        "customer",
        "service",
        "technician",
        "status",
        "preferred_date",
        "preferred_slot",
        "estimated_amount",
        "final_amount",
    )
    list_filter = ("status", "preferred_date")
    search_fields = (
        "booking_id",
        "customer__username",
        "service__name",
        "technician__user__username",
    )
    readonly_fields = ("booking_id",)
    date_hierarchy = "preferred_date"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_id",
        "booking",
        "amount",
        "status",
        "gateway",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("transaction_id", "booking__booking_id")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "booking",
        "technician",
        "customer",
        "rating",
        "is_hidden",
    )
    list_filter = ("rating", "is_hidden")
    actions = ("hide_reviews", "unhide_reviews")

    @admin.action(description="Hide selected reviews")
    def hide_reviews(self, request, queryset):
        queryset.update(is_hidden=True)

    @admin.action(description="Unhide selected reviews")
    def unhide_reviews(self, request, queryset):
        queryset.update(is_hidden=False)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "recipient",
        "title",
        "body",
        "is_read",
        "created_at",
    )
    list_filter = ("is_read",)
    search_fields = ("recipient__username", "title")


admin.site.register(User, UserAdmin)
