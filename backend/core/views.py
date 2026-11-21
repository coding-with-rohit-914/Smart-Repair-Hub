"""API views: auth (JWT/OTP), categories, bookings, payments, reviews, notifications."""
import math

from django.contrib.auth import authenticate
from django.db.models import Q
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (ApplianceCategory, Booking, Notification, Payment, Review,
                     Service, TechnicianProfile, User, notify)
from .serializers import (BookingCreateSerializer, BookingSerializer,
                          CategorySerializer, NotificationSerializer,
                          PaymentSerializer, ProfileSerializer,
                          ReviewSerializer, ServiceSerializer,
                          TechnicianProfileSerializer, UserSerializer)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if User.objects.filter(username=data["username"]).exists():
            return Response({"error": "Username already exists."}, status=400)
        role = data.get("role", User.Role.CUSTOMER)
        if role not in (User.Role.CUSTOMER, User.Role.TECHNICIAN):
            return Response({"error": "Invalid role."}, status=400)
        user = User.objects.create_user(
            username=data["username"], email=data.get("email", ""),
            password=data["password"], role=role, phone=data.get("phone", "")
        )
        if role == User.Role.TECHNICIAN:
            TechnicianProfile.objects.create(user=user)
        return Response(UserSerializer(user).data, status=201)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username", "").strip()
        password = request.data.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({"error": "Invalid credentials."}, status=401)
        if user.role == User.Role.TECHNICIAN:
            profile = getattr(user, "technician_profile", None)
            if profile and profile.approval_status == TechnicianProfile.ApprovalStatus.REJECTED:
                return Response({"error": "Your technician account was rejected."}, status=403)
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        })


class RequestOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get("phone", "").strip()
        user = User.objects.filter(phone=phone).first()
        if not user:
            return Response({"error": "No account with this phone number."}, status=404)
        otp = user.generate_otp()
        notify(user, "OTP", f"Your verification code is {otp}")
        # In dev the OTP is also returned so the flow is testable without an SMS gateway.
        return Response({"detail": "OTP sent.", "otp": otp})


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get("phone", "").strip()
        otp = request.data.get("otp", "").strip()
        user = User.objects.filter(phone=phone).first()
        if not user or not user.otp_code or user.otp_code != otp:
            return Response({"error": "Invalid OTP."}, status=400)
        user.is_phone_verified = True
        user.otp_code = ""
        user.save(update_fields=["is_phone_verified", "otp_code"])
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        })


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    def post(self, request):
        old = request.data.get("old_password", "")
        new = request.data.get("new_password", "")
        if not request.user.check_password(old):
            return Response({"error": "Wrong current password."}, status=400)
        if len(new) < 6:
            return Response({"error": "New password too short."}, status=400)
        request.user.set_password(new)
        request.user.save()
        return Response({"detail": "Password changed."})


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


def haversine_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(r * 2 * math.asin(math.sqrt(a)), 2)


class BookingListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        return BookingCreateSerializer if self.request.method == "POST" else BookingSerializer

    def get_queryset(self):
        u = self.request.user
        qs = Booking.objects.select_related("service", "technician", "customer").all()
        if u.role == User.Role.CUSTOMER:
            return qs.filter(customer=u)
        if u.role == User.Role.TECHNICIAN:
            profile = getattr(u, "technician_profile", None)
            if profile:
                return qs.filter(
                    Q(technician=profile) |
                    Q(status="PENDING", service__category__in=profile.expertise.all())
                )
            return qs.none()
        return qs  # admin

    def perform_create(self, serializer):
        service = serializer.validated_data["service"]
        booking = serializer.save(
            customer=self.request.user,
            estimated_amount=service.base_price,
        )
        notify(booking.customer, "Booking Confirmed",
               f"Your booking {booking.booking_id} has been created. We are finding a technician.")


class BookingDetailView(generics.RetrieveAPIView):
    serializer_class = BookingSerializer

    def get_queryset(self):
        u = self.request.user
        qs = Booking.objects.all()
        if u.role == User.Role.CUSTOMER:
            return qs.filter(customer=u)
        if u.role == User.Role.TECHNICIAN:
            return qs
        return qs


class TechnicianListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = TechnicianProfileSerializer

    def get_queryset(self):
        return TechnicianProfile.objects.filter(approval_status="APPROVED")


class TechnicianProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = TechnicianProfileSerializer

    def get_object(self):
        profile, _ = TechnicianProfile.objects.get_or_create(user=self.request.user)
        return profile


class AvailableTechniciansView(APIView):
    """Suggest nearby approved technicians for a booking (haversine distance)."""

    def get(self, request, pk):
        booking = Booking.objects.filter(pk=pk).first()
        if not booking:
            return Response({"error": "Booking not found."}, status=404)
        profs = TechnicianProfile.objects.filter(
            approval_status="APPROVED", is_available=True,
            expertise=booking.service.category,
        )
        data = []
        for p in profs:
            d = haversine_km(booking.latitude, booking.longitude, p.latitude, p.longitude)
            data.append({"id": p.id, "name": p.user.get_full_name() or p.user.username,
                         "distance_km": d, "rating": p.rating_avg})
        data.sort(key=lambda x: x["distance_km"] if x["distance_km"] is not None else 1e9)
        return Response(data)


class BookingActionView(APIView):
    """Technician actions on a booking."""

    ACTIONS = {
        "accept": ("ACCEPTED", "Technician accepted your booking."),
        "reject": ("REJECTED", "Technician rejected your booking."),
        "on_the_way": ("ON_THE_WAY", "Your technician is on the way."),
        "arrived": ("ARRIVED", "Your technician has arrived."),
        "start": ("IN_PROGRESS", "Service has started."),
        "complete": ("COMPLETED", "Service has been completed."),
    }

    def post(self, request, pk, action):
        booking = Booking.objects.filter(pk=pk).first()
        if not booking:
            return Response({"error": "Booking not found."}, status=404)
        if action not in self.ACTIONS:
            return Response({"error": "Unknown action."}, status=400)
        u = request.user

        if action == "accept":
            if u.role != User.Role.TECHNICIAN:
                return Response({"error": "Only technicians can accept."}, status=403)
            profile = getattr(u, "technician_profile", None)
            if not profile or profile.approval_status != "APPROVED":
                return Response({"error": "Technician not approved."}, status=403)
            booking.technician = profile
            booking.status = "ACCEPTED"
        elif action == "reject":
            if u.role != User.Role.TECHNICIAN:
                return Response({"error": "Only technicians can reject."}, status=403)
            if booking.technician and booking.technician.user == u:
                booking.technician = None
            booking.status = "REJECTED"
        else:
            if booking.technician is None or booking.technician.user != u:
                return Response({"error": "Not your booking."}, status=403)
            booking.status = self.ACTIONS[action][0]

        booking.save()
        if action == "complete":
            booking.final_amount = booking.final_amount or booking.estimated_amount
            booking.save(update_fields=["final_amount"])
        notify(booking.customer, "Booking Update",
               f"{booking.booking_id}: {self.ACTIONS[action][1]}")
        return Response(BookingSerializer(booking).data)


class CancelBookingView(APIView):
    def post(self, request, pk):
        booking = Booking.objects.filter(pk=pk).first()
        if not booking:
            return Response({"error": "Booking not found."}, status=404)
        u = request.user
        if booking.customer != u and u.role != User.Role.ADMIN and not u.is_superuser:
            return Response({"error": "Not allowed."}, status=403)
        if booking.status in ("COMPLETED", "PAID", "CLOSED", "CANCELLED"):
            return Response({"error": "Booking can no longer be cancelled."}, status=400)
        booking.status = "CANCELLED"
        booking.save()
        notify(booking.customer, "Booking Cancelled", f"{booking.booking_id} was cancelled.")
        if booking.technician:
            notify(booking.technician.user, "Booking Cancelled",
                   f"{booking.booking_id} was cancelled by the customer.")
        return Response(BookingSerializer(booking).data)


class AssignTechnicianView(APIView):
    """Admin manually assigns / reassigns a technician."""

    def post(self, request, pk):
        if request.user.role != User.Role.ADMIN and not request.user.is_superuser:
            return Response({"error": "Admin only."}, status=403)
        booking = Booking.objects.filter(pk=pk).first()
        if not booking:
            return Response({"error": "Booking not found."}, status=404)
        tech_id = request.data.get("technician_id")
        profile = TechnicianProfile.objects.filter(pk=tech_id).first()
        if not profile or profile.approval_status != "APPROVED":
            return Response({"error": "Technician not approved."}, status=400)
        booking.technician = profile
        booking.status = "ASSIGNED"
        booking.save()
        notify(profile.user, "New Job Assigned",
               f"You have been assigned booking {booking.booking_id}.")
        notify(booking.customer, "Technician Assigned",
               f"A technician has been assigned to {booking.booking_id}.")
        return Response(BookingSerializer(booking).data)


class StartPaymentView(APIView):
    """Creates a payment record. Mock gateway — swap in Razorpay/Stripe here."""

    def post(self, request, pk):
        booking = Booking.objects.filter(pk=pk).first()
        if not booking:
            return Response({"error": "Booking not found."}, status=404)
        if booking.customer != request.user:
            return Response({"error": "Not allowed."}, status=403)
        if booking.status not in ("COMPLETED", "PENDING", "ACCEPTED", "ASSIGNED", "IN_PROGRESS"):
            return Response({"error": "Payment not allowed in this state."}, status=400)
        amount = booking.final_amount or booking.estimated_amount
        payment, _ = Payment.objects.get_or_create(
            booking=booking, defaults={"amount": amount, "gateway": "mock"}
        )
        return Response({
            "payment": PaymentSerializer(payment).data,
            "checkout": {
                "gateway": "mock",
                "order_id": f"order_{payment.transaction_id}",
                "amount": float(amount),
                "note": "Simulated checkout. POST to /api/bookings/{id}/pay/confirm/ to finish.",
            },
        })


class ConfirmPaymentView(APIView):
    def post(self, request, pk):
        booking = Booking.objects.filter(pk=pk).first()
        if not booking:
            return Response({"error": "Booking not found."}, status=404)
        if booking.customer != request.user:
            return Response({"error": "Not allowed."}, status=403)
        payment = getattr(booking, "payment", None)
        if not payment:
            return Response({"error": "No payment initiated."}, status=400)
        payment.status = Payment.Status.SUCCESS
        payment.save(update_fields=["status"])
        booking.status = "PAID"
        booking.final_amount = payment.amount
        booking.save(update_fields=["status", "final_amount"])
        notify(booking.customer, "Payment Successful",
               f"Payment of Rs.{payment.amount} received for {booking.booking_id}.")
        return Response({"payment": PaymentSerializer(payment).data})


class ReviewCreateView(generics.CreateAPIView):
    serializer_class = ReviewSerializer

    def perform_create(self, serializer):
        booking = serializer.validated_data["booking"]
        if booking.customer != self.request.user:
            raise serializers.ValidationError({"error": "Not your booking."})
        if booking.status not in ("COMPLETED", "PAID", "CLOSED"):
            raise serializers.ValidationError({"error": "You can review only after completion."})
        if not booking.technician:
            raise serializers.ValidationError({"error": "No technician on this booking."})
        serializer.save(technician=booking.technician, customer=self.request.user)


class MyNotificationsView(generics.ListAPIView):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return self.request.user.notifications.order_by("-created_at")


class MarkNotificationReadView(APIView):
    def post(self, request, pk):
        n = request.user.notifications.filter(pk=pk).first()
        if not n:
            return Response({"error": "Not found."}, status=404)
        n.is_read = True
        n.save(update_fields=["is_read"])
        return Response({"detail": "marked read"})


class TechnicianEarningsView(APIView):
    def get(self, request):
        profile = getattr(request.user, "technician_profile", None)
        if not profile:
            return Response({"error": "Technician only."}, status=403)
        paid = Booking.objects.filter(technician=profile, status="PAID")
        completed = Booking.objects.filter(technician=profile, status="COMPLETED")
        return Response({
            "total_earnings": sum(float(b.final_amount or b.estimated_amount) for b in paid),
            "completed_jobs": completed.count(),
            "paid_jobs": paid.count(),
            "rating_avg": profile.rating_avg,
        })