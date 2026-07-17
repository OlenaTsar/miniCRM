from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    # write_only=True - можна надсилати але не отримувати назад
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name"]

    def create(self, validated_data):
        validated_data["email_verification_token"] = uuid.uuid4()

        return User.objects.create_user(**validated_data)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        try:
            user = User.objects.get(email=attrs["email"])
            if not user.is_active:
                raise PermissionDenied("Акаунт деактивовано.")
            if not user.is_verified:
                raise PermissionDenied("Акаунт не активовано. Перевірте email.")
        except User.DoesNotExist:
            pass  # super() поверне помилку про невірні дані

        return super().validate(attrs)


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(min_length=8, write_only=True)
