
"""API views: auth (JWT/OTP), categories, bookings, payments, reviews, notifications."""

import logging
import math
import os
import secrets

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from drf_spectacular.utils import extend_schema

from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    ApplianceCategory,
    Booking,
    Notification,
    Payment,
    Review,
    Service,
    TechnicianProfile,
    User,
    notify,
)

from .serializers import (
    BookingCreateSerializer,
    BookingSerializer,
    CategorySerializer,
    NotificationSerializer,
    PaymentSerializer,
    ProfileSerializer,
    ReviewSerializer,
    ServiceSerializer,
    TechnicianProfileSerializer,
    UserSerializer,
)


logger = logging.getLogger("core")

# Dev-only override: when "True", OTP responses include the OTP so you can
# test locally without console/SMS. NEVER enable in production.
OTP_DEV_MODE = os.getenv("OTP_DEV_MODE", "False").lower() in (
    "1",
    "true",
    "yes",
)


# --------------------------------------------------
# SCHEMA-ONLY SERIALIZERS
# --------------------------------------------------

class _LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class _RegisterRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    role = serializers.ChoiceField(
        choices=User.Role.choices,
        required=False,
        default=User.Role.CUSTOMER,
    )


class _OtpRequestSerializer(serializers.Serializer):
    phone = serializers.CharField()


class _OtpVerifyRequestSerializer(serializers.Serializer):
    phone = serializers.CharField()
    otp = serializers.CharField()


class _ChangePasswordRequestSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()


class _PasswordResetOtpRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class _PasswordResetOtpVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()


class _PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()
    new_password = serializers.CharField()


class _AuthResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


class _MessageResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class _AssignTechnicianRequestSerializer(serializers.Serializer):
    technician_id = serializers.IntegerField()


class _NearbyTechnicianSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    distance_km = serializers.FloatField(allow_null=True)
    rating = serializers.FloatField(allow_null=True)


class _CheckoutSerializer(serializers.Serializer):
    gateway = serializers.CharField()
    order_id = serializers.CharField()
    amount = serializers.FloatField()
    note = serializers.CharField()


class _StartPaymentResponseSerializer(serializers.Serializer):
    payment = PaymentSerializer()
    checkout = _CheckoutSerializer()


class _PaymentResponseSerializer(serializers.Serializer):
    payment = PaymentSerializer()


class _EarningsResponseSerializer(serializers.Serializer):
    total_earnings = serializers.FloatField()
    completed_jobs = serializers.IntegerField()
    paid_jobs = serializers.IntegerField()
    rating_avg = serializers.FloatField(allow_null=True)


# --------------------------------------------------
# AUTHENTICATION
# --------------------------------------------------

class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=_RegisterRequestSerializer,
        responses={201: UserSerializer, 400: None},
    )
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        if User.objects.filter(username=data["username"]).exists():
            return Response(
                {"error": "Username already exists."},
                status=400,
            )

        role = data.get("role", User.Role.CUSTOMER)

        if role not in (
            User.Role.CUSTOMER,
            User.Role.TECHNICIAN,
        ):
            return Response(
                {"error": "Invalid role."},
                status=400,
            )

        user = User.objects.create_user(
            username=data["username"],
            email=data.get("email", ""),
            password=data["password"],
            role=role,
            phone=data.get("phone", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
        )

        if role == User.Role.TECHNICIAN:
            TechnicianProfile.objects.create(user=user)

        logger.info(
            "New user registered (user_id=%s, role=%s).",
            user.pk,
            role,
        )

        return Response(
            UserSerializer(user).data,
            status=201,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=_LoginRequestSerializer,
        responses={200: _AuthResponseSerializer, 401: None},
    )
    def post(self, request):
        username = request.data.get("username", "").strip()
        password = request.data.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is None:
            # Log the username only; NEVER the password.
            logger.warning(
                "Failed login attempt (username=%s, ip=%s).",
                username,
                request.META.get("REMOTE_ADDR", "unknown"),
            )
            return Response(
                {"error": "Invalid credentials."},
                status=401,
            )

        if user.role == User.Role.TECHNICIAN:
            profile = getattr(
                user,
                "technician_profile",
                None,
            )

            if (
                profile
                and profile.approval_status
                == TechnicianProfile.ApprovalStatus.REJECTED
            ):
                logger.warning(
                    "Rejected technician login blocked (user_id=%s).",
                    user.pk,
                )
                return Response(
                    {"error": "Your technician account was rejected."},
                    status=403,
                )

        refresh = RefreshToken.for_user(user)

        logger.info(
            "Login successful (user_id=%s, role=%s).",
            user.pk,
            user.role,
        )

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        })


class RequestOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=_OtpRequestSerializer,
        responses={
            200: _MessageResponseSerializer,
            404: None,
            429: None,
        },
    )
    def post(self, request):
        phone = request.data.get("phone", "").strip()

        user = User.objects.filter(phone=phone).first()

        if not user:
            return Response(
                {"error": "No account with this phone number."},
                status=404,
            )

        # Rate limit resend abuse.
        if user.otp_in_cooldown():
            logger.warning(
                "OTP resend blocked by cooldown (user_id=%s).",
                user.pk,
            )
            return Response(
                {
                    "error": (
                        "Please wait before requesting another OTP. "
                        f"Try again in {user.OTP_RESEND_COOLDOWN_SECONDS} seconds."
                    )
                },
                status=429,
            )

        otp = user.generate_otp()

        notify(
            user,
            "OTP",
            f"Your verification code is {otp}",
        )

        logger.info(
            "Phone OTP generated (user_id=%s).",
            user.pk,
        )  # OTP value never logged

        response = {"detail": "OTP sent."}

        if OTP_DEV_MODE:
            # Local development convenience only.
            response["otp"] = otp

        return Response(response)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=_OtpVerifyRequestSerializer,
        responses={
            200: _AuthResponseSerializer,
            400: None,
            404: None,
            429: None,
        },
    )
    def post(self, request):
        phone = request.data.get("phone", "").strip()
        otp = request.data.get("otp", "").strip()

        user = User.objects.filter(phone=phone).first()

        if not user:
            return Response(
                {"error": "No account with this phone number."},
                status=404,
            )

        # Expiry check.
        if user.otp_is_expired():
            logger.warning(
                "Expired phone OTP rejected (user_id=%s).",
                user.pk,
            )
            return Response(
                {"error": "OTP has expired. Please request a new one."},
                status=400,
            )

        # Attempt limit (brute-force protection).
        if user.otp_attempts >= user.OTP_MAX_ATTEMPTS:
            logger.warning(
                "Phone OTP attempts exhausted (user_id=%s).",
                user.pk,
            )
            return Response(
                {"error": "Too many wrong attempts. Please request a new OTP."},
                status=429,
            )

        if not user.otp_code or user.otp_code != otp:
            user.otp_attempts += 1
            user.save(update_fields=["otp_attempts"])

            logger.warning(
                "Wrong phone OTP entered (user_id=%s, attempt=%s).",
                user.pk,
                user.otp_attempts,
            )

            return Response(
                {"error": "Invalid OTP."},
                status=400,
            )

        user.is_phone_verified = True
        user.otp_code = ""
        user.otp_attempts = 0

        user.save(
            update_fields=[
                "is_phone_verified",
                "otp_code",
                "otp_attempts",
            ]
        )

        refresh = RefreshToken.for_user(user)

        logger.info(
            "Phone OTP verified (user_id=%s).",
            user.pk,
        )

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        })


# --------------------------------------------------
# PROFILE
# --------------------------------------------------

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):

    @extend_schema(
        request=_ChangePasswordRequestSerializer,
        responses={200: _MessageResponseSerializer, 400: None},
    )
    def post(self, request):
        old_password = request.data.get("old_password", "")
        new_password = request.data.get("new_password", "")

        if not request.user.check_password(old_password):
            return Response(
                {"error": "Wrong current password."},
                status=400,
            )

        if len(new_password) < 6:
            return Response(
                {"error": "New password too short."},
                status=400,
            )

        request.user.set_password(new_password)
        request.user.save()

        logger.info(
            "Password changed (user_id=%s).",
            request.user.pk,
        )

        return Response({
            "detail": "Password changed.",
        })


# --------------------------------------------------
# FORGOT PASSWORD (EMAIL OTP)
# --------------------------------------------------

class RequestPasswordOtpView(APIView):
    """Forgot password, step 1: email -> hashed reset OTP."""

    permission_classes = [AllowAny]

    @extend_schema(
        request=_PasswordResetOtpRequestSerializer,
        responses={
            200: _MessageResponseSerializer,
            429: None,
        },
    )
    def post(self, request):
        email = request.data.get("email", "").strip().lower()

        user = User.objects.filter(email=email).first()

        # Generic response: never reveal whether the email is registered.
        generic = {
            "detail": (
                "If an account with this email exists, "
                "a password reset code has been sent."
            )
        }

        if not user:
            logger.info(
                "Password reset OTP requested for unknown email.",
            )
            return Response(generic)

        # Resend cooldown (same constant as the phone OTP flow).
        if user.otp_in_cooldown():
            logger.warning(
                "Password reset OTP resend blocked by cooldown (user_id=%s).",
                user.pk,
            )
            return Response(
                {
                    "error": (
                        "Please wait before requesting another code. "
                        f"Try again in {user.OTP_RESEND_COOLDOWN_SECONDS} seconds."
                    )
                },
                status=429,
            )

        otp = f"{secrets.randbelow(1000000):06d}"

        # Store only the PBKDF2 hash of the OTP, never the OTP itself.
        user.otp_hash = make_password(otp)
        user.otp_purpose = "PASSWORD_RESET"
        user.otp_attempts = 0
        user.otp_requested_at = timezone.now()

        user.save(
            update_fields=[
                "otp_hash",
                "otp_purpose",
                "otp_attempts",
                "otp_requested_at",
            ]
        )

        notify(
            user,
            "Password Reset",
            f"Your password reset code is {otp}",
        )

        logger.info(
            "Password reset OTP generated (user_id=%s).",
            user.pk,
        )  # OTP value never logged

        response = dict(generic)

        if OTP_DEV_MODE:
            # Local development convenience only.
            response["otp"] = otp

        return Response(response)


class VerifyPasswordOtpView(APIView):
    """Forgot password, step 2: confirm the code before showing the
    new-password form. The OTP stays valid for the final reset call."""

    permission_classes = [AllowAny]

    @extend_schema(
        request=_PasswordResetOtpVerifySerializer,
        responses={
            200: _MessageResponseSerializer,
            400: None,
            429: None,
        },
    )
    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        otp = request.data.get("otp", "").strip()

        user = User.objects.filter(email=email).first()

        if (
            not user
            or not user.otp_hash
            or user.otp_purpose != "PASSWORD_RESET"
        ):
            return Response(
                {"error": "Invalid or expired code."},
                status=400,
            )

        if user.otp_requested_at is None or user.otp_is_expired():
            return Response(
                {"error": "This code has expired. Please request a new one."},
                status=400,
            )

        if user.otp_attempts >= user.OTP_MAX_ATTEMPTS:
            logger.warning(
                "Password reset OTP attempts exhausted (user_id=%s).",
                user.pk,
            )
            return Response(
                {"error": "Too many wrong attempts. Please request a new code."},
                status=429,
            )

        if not check_password(otp, user.otp_hash):
            user.otp_attempts += 1
            user.save(update_fields=["otp_attempts"])

            logger.warning(
                "Wrong password reset OTP entered (user_id=%s, attempt=%s).",
                user.pk,
                user.otp_attempts,
            )

            return Response(
                {"error": "Invalid code."},
                status=400,
            )

        # Code is live; reset re-verifies it. Reset attempts so the user
        # gets full tries on the final reset call.
        user.otp_attempts = 0
        user.save(update_fields=["otp_attempts"])

        return Response({
            "detail": "Code verified. You can now set a new password.",
        })


class ResetPasswordView(APIView):
    """Forgot password, step 3: OTP + new password -> password changed."""

    permission_classes = [AllowAny]

    @extend_schema(
        request=_PasswordResetSerializer,
        responses={
            200: _MessageResponseSerializer,
            400: None,
            429: None,
        },
    )
    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        otp = request.data.get("otp", "").strip()
        new_password = request.data.get("new_password", "")

        user = User.objects.filter(email=email).first()

        if (
            not user
            or not user.otp_hash
            or user.otp_purpose != "PASSWORD_RESET"
        ):
            return Response(
                {"error": "Invalid or expired code."},
                status=400,
            )

        if user.otp_requested_at is None or user.otp_is_expired():
            return Response(
                {"error": "This code has expired. Please request a new one."},
                status=400,
            )

        if user.otp_attempts >= user.OTP_MAX_ATTEMPTS:
            return Response(
                {"error": "Too many wrong attempts. Please request a new code."},
                status=429,
            )

        if not check_password(otp, user.otp_hash):
            user.otp_attempts += 1
            user.save(update_fields=["otp_attempts"])

            logger.warning(
                "Wrong password reset OTP on reset (user_id=%s, attempt=%s).",
                user.pk,
                user.otp_attempts,
            )

            return Response(
                {"error": "Invalid code."},
                status=400,
            )

        if len(new_password) < 6:
            return Response(
                {"error": "New password too short."},
                status=400,
            )

        user.set_password(new_password)

        # Burn the OTP so it can never be reused.
        user.otp_hash = ""
        user.otp_purpose = ""
        user.otp_attempts = 0

        user.save(
            update_fields=[
                "password",
                "otp_hash",
                "otp_purpose",
                "otp_attempts",
            ]
        )

        logger.info(
            "Password reset via OTP (user_id=%s).",
            user.pk,
        )

        return Response({
            "detail": "Password reset successful. Please log in with your new password.",
        })


# --------------------------------------------------
# CATEGORIES AND SERVICES
# --------------------------------------------------

class CategoryListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    queryset = ApplianceCategory.objects.all()


class ServiceListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ServiceSerializer

    def get_queryset(self):
        qs = Service.objects.filter(is_active=True)

        category = self.request.query_params.get("category")

        if category:
            qs = qs.filter(category_id=category)

        return qs


# --------------------------------------------------
# DISTANCE CALCULATION
# --------------------------------------------------

def haversine_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None

    radius = 6371.0

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1)
        * math.cos(p2)
        * math.sin(dl / 2) ** 2
    )

    return round(
        radius * 2 * math.asin(math.sqrt(a)),
        2,
    )


# --------------------------------------------------
# BOOKINGS
# --------------------------------------------------

class BookingListCreateView(generics.ListCreateAPIView):

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BookingCreateSerializer

        return BookingSerializer

    def get_queryset(self):
        user = self.request.user

        qs = Booking.objects.select_related(
            "service",
            "technician",
            "customer",
        )

        if user.role == User.Role.CUSTOMER:
            return qs.filter(customer=user)

        if user.role == User.Role.TECHNICIAN:
            profile = getattr(
                user,
                "technician_profile",
                None,
            )

            if not profile:
                return qs.none()

            return qs.filter(
                Q(technician=profile)
                | Q(
                    status="PENDING",
                    service__category__in=profile.expertise.all(),
                )
            )

        return qs

    def perform_create(self, serializer):
        service = serializer.validated_data["service"]

        booking = serializer.save(
            customer=self.request.user,
            estimated_amount=service.base_price,
        )

        notify(
            booking.customer,
            "Booking Confirmed",
            (
                f"Your booking {booking.booking_id} has been created. "
                "We are finding a technician."
            ),
        )


class BookingDetailView(generics.RetrieveAPIView):
    serializer_class = BookingSerializer

    def get_queryset(self):
        user = self.request.user

        qs = Booking.objects.select_related(
            "service",
            "technician",
            "customer",
        )

        if user.role == User.Role.CUSTOMER:
            return qs.filter(customer=user)

        if user.role == User.Role.TECHNICIAN:
            profile = getattr(
                user,
                "technician_profile",
                None,
            )

            if not profile:
                return qs.none()

            return qs.filter(
                Q(technician=profile)
                | Q(
                    status="PENDING",
                    service__category__in=profile.expertise.all(),
                )
            )

        return qs


# --------------------------------------------------
# TECHNICIANS
# --------------------------------------------------

class TechnicianListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = TechnicianProfileSerializer

    def get_queryset(self):
        return TechnicianProfile.objects.filter(
            approval_status="APPROVED",
        )


class TechnicianProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = TechnicianProfileSerializer

    def get_object(self):
        profile, _ = TechnicianProfile.objects.get_or_create(
            user=self.request.user,
        )

        return profile


class AvailableTechniciansView(APIView):
    """Suggest nearby approved technicians for a booking."""

    @extend_schema(
        responses={
            200: _NearbyTechnicianSerializer(many=True),
            403: None,
            404: None,
        },
    )
    def get(self, request, pk):
        booking = Booking.objects.filter(pk=pk).first()

        if not booking:
            return Response(
                {"error": "Booking not found."},
                status=404,
            )

        user = request.user

        if (
            booking.customer != user
            and user.role != User.Role.ADMIN
            and not user.is_superuser
        ):
            return Response(
                {"error": "Not allowed."},
                status=403,
            )

        profiles = TechnicianProfile.objects.filter(
            approval_status="APPROVED",
            is_available=True,
            expertise=booking.service.category,
        ).select_related("user").distinct()

        data = []

        for profile in profiles:
            distance = haversine_km(
                booking.latitude,
                booking.longitude,
                profile.latitude,
                profile.longitude,
            )

            data.append({
                "id": profile.id,
                "name": (
                    profile.user.get_full_name()
                    or profile.user.username
                ),
                "distance_km": distance,
                "rating": profile.rating_avg,
            })

        data.sort(
            key=lambda item: (
                item["distance_km"]
                if item["distance_km"] is not None
                else 1e9
            )
        )

        return Response(data)


# --------------------------------------------------
# BOOKING ACTIONS
# --------------------------------------------------

class BookingActionView(APIView):
    """Technician actions on a booking."""

    ACTIONS = {
        "accept": (
            "ACCEPTED",
            "Technician accepted your booking.",
        ),
        "reject": (
            "REJECTED",
            "Technician rejected your booking.",
        ),
        "on_the_way": (
            "ON_THE_WAY",
            "Your technician is on the way.",
        ),
        "arrived": (
            "ARRIVED",
            "Your technician has arrived.",
        ),
        "start": (
            "IN_PROGRESS",
            "Service has started.",
        ),
        "complete": (
            "COMPLETED",
            "Service has been completed.",
        ),
    }

    @extend_schema(
        operation_id="booking_action",
        request=None,
        responses={
            200: BookingSerializer,
            400: None,
            403: None,
            404: None,
        },
    )
    def post(self, request, pk, action):
        if action not in self.ACTIONS:
            return Response(
                {"error": "Unknown action."},
                status=400,
            )

        user = request.user

        if user.role != User.Role.TECHNICIAN:
            return Response(
                {"error": "Only technicians can perform this action."},
                status=403,
            )

        profile = getattr(
            user,
            "technician_profile",
            None,
        )

        if (
            not profile
            or profile.approval_status
            != TechnicianProfile.ApprovalStatus.APPROVED
        ):
            return Response(
                {"error": "Technician not approved."},
                status=403,
            )

        with transaction.atomic():
            booking = (
                Booking.objects.select_for_update()
                .filter(pk=pk)
                .first()
            )

            if not booking:
                return Response(
                    {"error": "Booking not found."},
                    status=404,
                )

            if action == "accept":
                if booking.status != "PENDING":
                    return Response(
                        {"error": "This booking is no longer available."},
                        status=400,
                    )

                if booking.technician is not None:
                    return Response(
                        {"error": "This booking is already assigned."},
                        status=400,
                    )

                if not profile.is_available:
                    return Response(
                        {"error": "You are currently unavailable."},
                        status=400,
                    )

                if not profile.expertise.filter(
                    pk=booking.service.category_id
                ).exists():
                    return Response(
                        {"error": "This service is not in your expertise."},
                        status=403,
                    )

                booking.technician = profile
                booking.status = "ACCEPTED"

            elif action == "reject":
                if booking.technician != profile:
                    return Response(
                        {"error": "This booking is not assigned to you."},
                        status=403,
                    )

                if booking.status not in (
                    "ASSIGNED",
                    "ACCEPTED",
                ):
                    return Response(
                        {"error": "This booking cannot be rejected now."},
                        status=400,
                    )

                booking.technician = None
                booking.status = "PENDING"

            else:
                if booking.technician != profile:
                    return Response(
                        {"error": "This booking is not assigned to you."},
                        status=403,
                    )

                allowed_transitions = {
                    "on_the_way": ("ACCEPTED", "ASSIGNED"),
                    "arrived": ("ON_THE_WAY",),
                    "start": ("ARRIVED",),
                    "complete": ("IN_PROGRESS",),
                }

                allowed_states = allowed_transitions[action]

                if booking.status not in allowed_states:
                    return Response(
                        {
                            "error": (
                                f"Action '{action}' is not allowed "
                                f"when booking status is '{booking.status}'."
                            )
                        },
                        status=400,
                    )

                booking.status = self.ACTIONS[action][0]

                if action == "complete":
                    booking.final_amount = (
                        booking.final_amount
                        or booking.estimated_amount
                    )

            booking.save()

        notify(
            booking.customer,
            "Booking Update",
            (
                f"{booking.booking_id}: "
                f"{self.ACTIONS[action][1]}"
            ),
        )

        return Response(
            BookingSerializer(booking).data,
        )


# --------------------------------------------------
# CANCEL BOOKING
# --------------------------------------------------

class CancelBookingView(APIView):

    @extend_schema(
        request=None,
        responses={
            200: BookingSerializer,
            400: None,
            403: None,
            404: None,
        },
    )
    def post(self, request, pk):
        booking = Booking.objects.filter(pk=pk).first()

        if not booking:
            return Response(
                {"error": "Booking not found."},
                status=404,
            )

        user = request.user

        if (
            booking.customer != user
            and user.role != User.Role.ADMIN
            and not user.is_superuser
        ):
            return Response(
                {"error": "Not allowed."},
                status=403,
            )

        if booking.status in (
            "COMPLETED",
            "PAID",
            "CLOSED",
            "CANCELLED",
        ):
            return Response(
                {"error": "Booking can no longer be cancelled."},
                status=400,
            )

        booking.status = "CANCELLED"
        booking.save(update_fields=["status"])

        notify(
            booking.customer,
            "Booking Cancelled",
            f"{booking.booking_id} was cancelled.",
        )

        if booking.technician:
            notify(
                booking.technician.user,
                "Booking Cancelled",
                f"{booking.booking_id} was cancelled.",
            )

        return Response(
            BookingSerializer(booking).data,
        )


# --------------------------------------------------
# ADMIN ASSIGN TECHNICIAN
# --------------------------------------------------

class AssignTechnicianView(APIView):
    """Admin manually assigns a technician."""

    @extend_schema(
        request=_AssignTechnicianRequestSerializer,
        responses={
            200: BookingSerializer,
            400: None,
            403: None,
            404: None,
        },
    )
    def post(self, request, pk):
        user = request.user

        if (
            user.role != User.Role.ADMIN
            and not user.is_superuser
        ):
            return Response(
                {"error": "Admin only."},
                status=403,
            )

        booking = Booking.objects.filter(pk=pk).first()

        if not booking:
            return Response(
                {"error": "Booking not found."},
                status=404,
            )

        tech_id = request.data.get("technician_id")

        profile = TechnicianProfile.objects.filter(
            pk=tech_id,
            approval_status="APPROVED",
        ).select_related("user").first()

        if not profile:
            return Response(
                {"error": "Technician not approved."},
                status=400,
            )

        if not profile.expertise.filter(
            pk=booking.service.category_id
        ).exists():
            return Response(
                {"error": "Technician does not support this service."},
                status=400,
            )

        if not profile.is_available:
            return Response(
                {"error": "Technician is currently unavailable."},
                status=400,
            )

        booking.technician = profile
        booking.status = "ASSIGNED"
        booking.save(
            update_fields=["technician", "status"]
        )

        notify(
            profile.user,
            "New Job Assigned",
            f"You have been assigned booking {booking.booking_id}.",
        )

        notify(
            booking.customer,
            "Technician Assigned",
            f"A technician has been assigned to {booking.booking_id}.",
        )

        return Response(
            BookingSerializer(booking).data,
        )


# --------------------------------------------------
# PAYMENTS
# --------------------------------------------------

class StartPaymentView(APIView):
    """Creates a payment record. Mock gateway only."""

    @extend_schema(
        request=None,
        responses={
            200: _StartPaymentResponseSerializer,
            400: None,
            403: None,
            404: None,
        },
    )
    def post(self, request, pk):
        booking = Booking.objects.filter(pk=pk).first()

        if not booking:
            return Response(
                {"error": "Booking not found."},
                status=404,
            )

        if booking.customer != request.user:
            return Response(
                {"error": "Not allowed."},
                status=403,
            )

        if booking.status not in (
            "COMPLETED",
            "PENDING",
            "ACCEPTED",
            "ASSIGNED",
            "IN_PROGRESS",
        ):
            return Response(
                {"error": "Payment not allowed in this state."},
                status=400,
            )

        amount = (
            booking.final_amount
            or booking.estimated_amount
        )

        payment, _ = Payment.objects.get_or_create(
            booking=booking,
            defaults={
                "amount": amount,
                "gateway": "mock",
            },
        )

        if payment.status == Payment.Status.SUCCESS:
            return Response(
                {"error": "Payment has already been completed."},
                status=400,
            )

        return Response({
            "payment": PaymentSerializer(payment).data,
            "checkout": {
                "gateway": "mock",
                "order_id": f"order_{payment.transaction_id}",
                "amount": float(amount),
                "note": (
                    "Simulated checkout. "
                    f"POST to /api/bookings/{pk}/pay/confirm/ to finish."
                ),
            },
        })


class ConfirmPaymentView(APIView):

    @extend_schema(
        request=None,
        responses={
            200: _PaymentResponseSerializer,
            400: None,
            403: None,
            404: None,
        },
    )
    def post(self, request, pk):
        booking = Booking.objects.filter(pk=pk).first()

        if not booking:
            return Response(
                {"error": "Booking not found."},
                status=404,
            )

        if booking.customer != request.user:
            return Response(
                {"error": "Not allowed."},
                status=403,
            )

        payment = getattr(
            booking,
            "payment",
            None,
        )

        if not payment:
            return Response(
                {"error": "No payment initiated."},
                status=400,
            )

        if payment.status == Payment.Status.SUCCESS:
            return Response(
                {"error": "Payment already completed."},
                status=400,
            )

        if booking.status not in (
            "COMPLETED",
            "PENDING",
            "ACCEPTED",
            "ASSIGNED",
            "IN_PROGRESS",
        ):
            return Response(
                {"error": "Payment not allowed in this state."},
                status=400,
            )

        payment.status = Payment.Status.SUCCESS
        payment.save(update_fields=["status"])

        booking.status = "PAID"
        booking.final_amount = payment.amount

        booking.save(
            update_fields=[
                "status",
                "final_amount",
            ]
        )

        notify(
            booking.customer,
            "Payment Successful",
            (
                f"Payment of Rs.{payment.amount} received "
                f"for {booking.booking_id}."
            ),
        )

        logger.info(
            "Payment confirmed (booking=%s, transaction=%s).",
            booking.booking_id,
            payment.transaction_id,
        )

        return Response({
            "payment": PaymentSerializer(payment).data,
        })


# --------------------------------------------------
# REVIEWS
# --------------------------------------------------

class ReviewCreateView(generics.CreateAPIView):
    serializer_class = ReviewSerializer

    def perform_create(self, serializer):
        booking = serializer.validated_data["booking"]

        if booking.customer != self.request.user:
            raise serializers.ValidationError(
                {"error": "Not your booking."}
            )

        if booking.status not in (
            "COMPLETED",
            "PAID",
            "CLOSED",
        ):
            raise serializers.ValidationError(
                {"error": "You can review only after completion."}
            )

        if not booking.technician:
            raise serializers.ValidationError(
                {"error": "No technician on this booking."}
            )

        serializer.save(
            technician=booking.technician,
            customer=self.request.user,
        )


# --------------------------------------------------
# NOTIFICATIONS
# --------------------------------------------------

class MyNotificationsView(generics.ListAPIView):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return self.request.user.notifications.order_by(
            "-created_at"
        )


class MarkNotificationReadView(APIView):

    @extend_schema(
        request=None,
        responses={
            200: _MessageResponseSerializer,
            404: None,
        },
    )
    def post(self, request, pk):
        notification = (
            request.user.notifications
            .filter(pk=pk)
            .first()
        )

        if not notification:
            return Response(
                {"error": "Not found."},
                status=404,
            )

        notification.is_read = True

        notification.save(
            update_fields=["is_read"]
        )

        return Response({
            "detail": "marked read",
        })


# --------------------------------------------------
# TECHNICIAN EARNINGS
# --------------------------------------------------

class TechnicianEarningsView(APIView):

    @extend_schema(
        responses={
            200: _EarningsResponseSerializer,
            403: None,
        },
    )
    def get(self, request):
        profile = getattr(
            request.user,
            "technician_profile",
            None,
        )

        if (
            request.user.role != User.Role.TECHNICIAN
            or not profile
        ):
            return Response(
                {"error": "Technician only."},
                status=403,
            )

        paid = Booking.objects.filter(
            technician=profile,
            status="PAID",
        )

        completed = Booking.objects.filter(
            technician=profile,
            status="COMPLETED",
        )

        return Response({
            "total_earnings": sum(
                float(
                    booking.final_amount
                    or booking.estimated_amount
                )
                for booking in paid
            ),
            "completed_jobs": completed.count(),
            "paid_jobs": paid.count(),
            "rating_avg": profile.rating_avg,
        })
