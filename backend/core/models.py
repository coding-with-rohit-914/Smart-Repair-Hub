"""Core models: users, categories, services, bookings, payments, reviews, notifications."""
import random
import secrets

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        TECHNICIAN = "TECHNICIAN", "Technician"
        ADMIN = "ADMIN", "Admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    phone = models.CharField(max_length=15, blank=True, default="")
    otp_code = models.CharField(max_length=6, blank=True, default="")
    otp_requested_at = models.DateTimeField(null=True, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    def generate_otp(self):
        self.otp_code = f"{random.randint(100000, 999999)}"
        self.save(update_fields=["otp_code", "otp_requested_at"])
        return self.otp_code


class ApplianceCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)  # AC / TV / Fridge
    icon = models.CharField(max_length=10, blank=True, default="")
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Appliance Category"
        verbose_name_plural = "Appliance Categories"

    def __str__(self):
        return self.name


class Service(models.Model):
    category = models.ForeignKey(ApplianceCategory, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=100)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("category", "name")

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class TechnicianProfile(models.Model):
    class ApprovalStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="technician_profile")
    expertise = models.ManyToManyField(ApplianceCategory, related_name="technicians")
    experience_years = models.PositiveIntegerField(default=0)
    photo = models.ImageField(upload_to="technicians/", blank=True, null=True)
    bio = models.TextField(blank=True, default="")
    address = models.TextField(blank=True, default="")
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    is_available = models.BooleanField(default=True)
    approval_status = models.CharField(
        max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING
    )
    rating_avg = models.FloatField(default=0.0)
    rating_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Technician: {self.user.username}"

    def recalc_rating(self):
        reviews = self.reviews.all()
        self.rating_count = reviews.count()
        self.rating_avg = round(sum(r.rating for r in reviews) / reviews.count(), 2) if reviews else 0.0
        self.save(update_fields=["rating_avg", "rating_count"])


class BookingStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ASSIGNED = "ASSIGNED", "Technician Assigned"
    ACCEPTED = "ACCEPTED", "Accepted"
    ON_THE_WAY = "ON_THE_WAY", "On the Way"
    ARRIVED = "ARRIVED", "Technician Arrived"
    IN_PROGRESS = "IN_PROGRESS", "Service Started"
    COMPLETED = "COMPLETED", "Service Completed"
    PAID = "PAID", "Payment Completed"
    CLOSED = "CLOSED", "Closed"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


class Booking(models.Model):
    booking_id = models.CharField(max_length=20, unique=True, editable=False)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="bookings")
    technician = models.ForeignKey(TechnicianProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings")
    status = models.CharField(max_length=15, choices=BookingStatus.choices, default=BookingStatus.PENDING)
    problem_description = models.TextField()
    preferred_date = models.DateField()
    preferred_slot = models.CharField(max_length=20)
    address = models.TextField()
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    images = models.ImageField(upload_to="bookings/", blank=True, null=True)
    instructions = models.TextField(blank=True, default="")
    estimated_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    technician_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.booking_id:
            # SRV-2026-00125 style ID
            prefix = f"SRV-{self.created_at.year if self.created_at else ''}"
            while True:
                code = f"SRV-{secrets.token_hex(2).upper()}-{random.randint(1000, 9999)}"
                if not Booking.objects.filter(booking_id=code).exists():
                    self.booking_id = code
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return self.booking_id


class Payment(models.Model):
    class Status(models.TextChoices):
        INITIATED = "INITIATED", "Initiated"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="payment")
    transaction_id = models.CharField(max_length=50, unique=True, editable=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.INITIATED)
    gateway = models.CharField(max_length=30, default="mock")
    gateway_order_id = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = f"TXN-{secrets.token_hex(6).upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.transaction_id


class Review(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="review")
    technician = models.ForeignKey(TechnicianProfile, on_delete=models.CASCADE, related_name="reviews")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    is_hidden = models.BooleanField(default=False)  # admin moderation

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        if created or not kwargs.get("update_fields"):
            self.technician.recalc_rating()

    def __str__(self):
        return f"{self.booking.booking_id} - {self.rating}★"


class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=100)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.recipient.username}: {self.title}"


def notify(recipient, title, body):
    """Create an in-app notification (and print for FCM integration)."""
    if recipient:
        Notification.objects.create(recipient=recipient, title=title, body=body)
        # TODO: replace print with pyfcm/firebase-admin push notification
        print(f"[FCM stub] -> {recipient.username}: {title} | {body}")