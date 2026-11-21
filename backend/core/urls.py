from django.urls import path

from . import views

urlpatterns = [
    # Auth
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/otp/request/", views.RequestOTPView.as_view(), name="otp-request"),
    path("auth/otp/verify/", views.VerifyOTPView.as_view(), name="otp-verify"),
    path("auth/profile/", views.ProfileView.as_view(), name="profile"),
    path("auth/change-password/", views.ChangePasswordView.as_view(), name="change-password"),

    # Catalog
    path("categories/", views.CategoryListView.as_view(), name="categories"),
    path("services/", views.ServiceListView.as_view(), name="services"),

    # Bookings
    path("bookings/", views.BookingListCreateView.as_view(), name="bookings"),
    path("bookings/<int:pk>/", views.BookingDetailView.as_view(), name="booking-detail"),
    path("bookings/<int:pk>/cancel/", views.CancelBookingView.as_view(), name="booking-cancel"),
    path("bookings/<int:pk>/assign-technician/", views.AssignTechnicianView.as_view(), name="assign"),
    path("bookings/<int:pk>/available-technicians/", views.AvailableTechniciansView.as_view(), name="available-techs"),
    path("bookings/<int:pk>/<str:action>/", views.BookingActionView.as_view(), name="booking-action"),

    # Payments
    path("bookings/<int:pk>/pay/", views.StartPaymentView.as_view(), name="pay"),
    path("bookings/<int:pk>/pay/confirm/", views.ConfirmPaymentView.as_view(), name="pay-confirm"),

    # Reviews
    path("reviews/", views.ReviewCreateView.as_view(), name="review-create"),

    # Notifications
    path("notifications/", views.MyNotificationsView.as_view(), name="notifications"),
    path("notifications/<int:pk>/read/", views.MarkNotificationReadView.as_view(), name="notif-read"),

    # Technicians
    path("technicians/", views.TechnicianListView.as_view(), name="technicians"),
    path("technician/profile/", views.TechnicianProfileView.as_view(), name="tech-profile"),
    path("technician/earnings/", views.TechnicianEarningsView.as_view(), name="tech-earnings"),
]
