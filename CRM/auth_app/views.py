from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

from .serializers import RegisterSerializer, CustomTokenObtainPairSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        self._send_verification_email(user)

    def _send_verification_email(self, user):
        link = f"{settings.FRONTEND_URL}/api/auth/verify-email/{user.email_verification_token}"
        send_mail(
            subject="Confirm your email",
            message=f"Click the link to activate your account:\n{link}",
            from_email="noreply@minicrm.com",
            recipient_list=[user.email],
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
