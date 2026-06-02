from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model

from .serializers import (
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
)
from .tasks import send_verification_email, send_password_reset_email

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        send_verification_email.delay(
            user.email,
            str(user.email_verification_token)
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            user = User.objects.get(email_verification_token=token, is_verified=False)
            user.is_verified = True
            user.email_verification_token = None
            user.save()
            return Response({"detail": "Email підтверджено. Можете увійти."})
        except User.DoesNotExist:
            return Response({"detail": "Невалідний токен."}, status=400)


# login
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# logout
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Успішно вийшли."})
        except TokenError:
            return Response({"detail": "Невалідний токен."}, status=400)


class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
            user.generate_password_reset_token()
            send_password_reset_email.delay(
                email,
                str(user.password_reset_token)
            )
        except User.DoesNotExist:
            pass  # не повідомляємо чи існує email — захист від перебору

        return Response({"detail": "If this email exists, you will receive a reset link."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, token):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_password = serializer.validated_data["new_password"]

        try:
            user = User.objects.get(password_reset_token=token)
        except User.DoesNotExist:
            return Response({"detail": "Невалідний токен."}, status=400)

        if not user.is_password_reset_token_valid():
            return Response({"detail": "Токен застарів."}, status=400)

        # змінюємо пароль і видаляємо токен
        user.set_password(new_password)
        user.password_reset_token = None
        user.password_reset_token_expires = None
        user.save()

        return Response({"detail": "Пароль успішно змінено."})
