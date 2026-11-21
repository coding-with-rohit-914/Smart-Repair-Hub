from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (ApplianceCategory, Booking, Notification, Payment, Review,
                     Service, TechnicianProfile, User)


class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "phone", "role", "is_active")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Extra", {"fields": ("role", "phone", "is_phone_verified", "avatar")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Extra", {"fields": ("role", "phone")}),
    )
    list_filter = BaseUserAdmin.list_filter + ("role",)


@admin.register(ApplianceCategory)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "icon")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "name", "base_price", "is_active")
    list_filter = ("category", "is_active")


@admin.register(TechnicianProfile)
class TechnicianAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "experience_years", "approval_status", "is_available", "rating_avg")
    list_filter = ("approval_status", "is_available")
    search_fields = ("user__username", "user__phone")
    filter_horizontal = ("expertise",)
    actions = ("approve_technicians", "reject_technicians")

    @admin.action(description="Approve selected technicians")
    def approve_technicians(self, request, queryset):
        queryset.update(approval_status="APPROVED")

    @admin.action(description="Reject selected technicians")
    def reject_technicians(self, request, queryset):
        queryset.update(approval_status="REJECTED")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("booking_id", "customer", "service", "technician", "status",
                    "preferred_date", "preferred_slot", "estimated_amount")
    list_filter = ("status", "preferred_date")
    search_fields = ("booking_id", "customer__username", "service__name")
    readonly_fields = ("booking_id",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "booking", "amount", "status", "gateway", "created_at")
    list_filter = ("status",)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("booking", "technician", "customer", "rating", "is_hidden")
    list_filter = ("rating", "is_hidden")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "title", "is_read", "created_at")
    list_filter = ("is_read",)

admin.site.register(User, UserAdmin)