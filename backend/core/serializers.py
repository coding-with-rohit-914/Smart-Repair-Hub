
from rest_framework import serializers

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


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "phone",
            "role",
            "password",
            "first_name",
            "last_name",
            "avatar",
        )


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "phone",
            "role",
            "first_name",
            "last_name",
            "avatar",
        )
        read_only_fields = ("id", "role")


class TechnicianProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )
    email = serializers.CharField(
        source="user.email",
        read_only=True,
    )
    phone = serializers.CharField(
        source="user.phone",
        read_only=True,
    )
    full_name = serializers.SerializerMethodField()

    expertise = serializers.SlugRelatedField(
        slug_field="name",
        queryset=ApplianceCategory.objects.all(),
        many=True,
    )

    class Meta:
        model = TechnicianProfile
        fields = (
            "id",
            "username",
            "email",
            "phone",
            "full_name",
            "expertise",
            "experience_years",
            "photo",
            "bio",
            "address",
            "latitude",
            "longitude",
            "is_available",
            "approval_status",
            "rating_avg",
            "rating_count",
        )
        read_only_fields = (
            "id",
            "username",
            "email",
            "phone",
            "full_name",
            "approval_status",
            "rating_avg",
            "rating_count",
        )

    def get_full_name(self, obj):
        return obj.user.get_full_name()


class CategorySerializer(serializers.ModelSerializer):
    services = serializers.SerializerMethodField()

    class Meta:
        model = ApplianceCategory
        fields = (
            "id",
            "name",
            "icon",
            "description",
            "services",
        )

    def get_services(self, obj):
        return ServiceSerializer(
            obj.services.filter(is_active=True),
            many=True,
        ).data


class ServiceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    class Meta:
        model = Service
        fields = (
            "id",
            "category",
            "category_name",
            "name",
            "base_price",
            "description",
            "is_active",
        )


class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = (
            "service",
            "problem_description",
            "preferred_date",
            "preferred_slot",
            "address",
            "latitude",
            "longitude",
            "images",
            "instructions",
        )

    def validate_service(self, value):
        if not value.is_active:
            raise serializers.ValidationError(
                "This service is not active."
            )
        return value


class BookingSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)
    technician = TechnicianProfileSerializer(read_only=True)

    service_detail = ServiceSerializer(
        source="service",
        read_only=True,
    )

    has_payment = serializers.SerializerMethodField()
    has_review = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = "__all__"
        read_only_fields = (
            "booking_id",
            "status",
            "customer",
            "technician",
            "estimated_amount",
            "final_amount",
            "technician_notes",
        )

    def get_has_payment(self, obj):
        return (
            hasattr(obj, "payment")
            and obj.payment.status == Payment.Status.SUCCESS
        )

    def get_has_review(self, obj):
        return hasattr(obj, "review")


class PaymentSerializer(serializers.ModelSerializer):
    booking_code = serializers.CharField(
        source="booking.booking_id",
        read_only=True,
    )

    class Meta:
        model = Payment
        fields = (
            "transaction_id",
            "booking_code",
            "amount",
            "status",
            "gateway",
            "created_at",
        )


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = (
            "id",
            "booking",
            "technician",
            "rating",
            "comment",
            "created_at",
        )
        read_only_fields = (
            "technician",
        )


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "title",
            "body",
            "is_read",
            "created_at",
        )
