
"""Forgot-password / email-OTP flow.

New endpoints (existing auth endpoints untouched):
    POST /api/auth/password-reset/request/  {email}
    POST /api/auth/password-reset/confirm/  {email, otp, new_password}

Security:
    - OTP stored hashed (never plaintext)
    - 10 min expiry, max 5 wrong attempts, 60s resend cooldown
    - OTP NEVER returned in API response
    - OTP/password never written to logs
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, notify


logger = logging.getLogger("core")

OTP_PURPOSE = "PASSWORD_RESET"


class RequestPasswordResetOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()

        if not email:
            return Response(
                {"error": "Email is required."},
                status=400,
            )

        user = User.objects.filter(email__iexact=email).first()

        if not user:
            # Do not reveal whether the email exists beyond a clear
            # demo-friendly message (registration already reveals usernames).
            return Response(
                {"error": "No account found with this email."},
                status=404,
            )

        if user.otp_in_cooldown():
            return Response(
                {
                    "error": (
                        "Please wait before requesting another OTP. "
                        f"Try again in {user.OTP_RESEND_COOLDOWN_SECONDS} seconds."
                    )
                },
                status=429,
            )

        raw_otp = user.set_otp(OTP_PURPOSE)

        try:
            send_mail(
                subject="Smart Repair Hub — Password Reset OTP",
                message=(
                    f"Hello {user.username or 'there'},\n\n"
                    f"Your password reset OTP is: {raw_otp}\n\n"
                    f"It expires in {user.OTP_EXPIRY_MINUTES} minutes.\n"
                    "If you did not request this, you can safely ignore this email.\n\n"
                    "— Smart Repair Hub"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception:
            # Never log the OTP; log only the failure + user id.
            logger.exception(
                "Password reset email failed to send (user_id=%s).",
                user.pk,
            )
            return Response(
                {
                    "error": (
                        "Could not send the email right now. "
                        "Please try again in a minute."
                    )
                },
                status=502,
            )

        logger.info(
            "Password reset OTP sent (user_id=%s, email domain ok).",
            user.pk,
        )

        return Response(
            {"detail": "OTP sent to your email."},
            status=200,
        )


class ConfirmPasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        otp = (request.data.get("otp") or "").strip()
        new_password = request.data.get("new_password") or ""

        if not email or not otp or not new_password:
            return Response(
                {"error": "Email, OTP and new password are required."},
                status=400,
            )

        if len(new_password) < 6:
            return Response(
                {"error": "New password must be at least 6 characters."},
                status=400,
            )

        user = User.objects.filter(email__iexact=email).first()

        if not user:
            return Response(
                {"error": "No account found with this email."},
                status=404,
            )

        ok, err = user.check_otp(otp, OTP_PURPOSE)

        if not ok:
            return Response(
                {"error": err},
                status=400,
            )

        user.set_password(new_password)
        user.clear_otp()  # also invalidates the OTP just used

        notify(
            user,
            "Password Changed",
            "Your password was reset successfully. If this wasn't you, contact support immediately.",
        )

        logger.info(
            "Password reset completed (user_id=%s).",
            user.pk,
        )

        return Response(
            {
                "detail": (
                    "Password reset successful. "
                    "Please log in with your new password."
                )
            },
            status=200,
        )
