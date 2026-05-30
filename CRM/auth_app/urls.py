from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    VerifyEmailView,
    CustomTokenObtainPairView,
    LogoutView,
    PasswordResetView,
    PasswordResetConfirmView,
)

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("verify-email/<uuid:token>/", VerifyEmailView.as_view()),
    path("login/", CustomTokenObtainPairView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("password-reset/", PasswordResetView.as_view()),
    path("password-reset/confirm/<uuid:token>/", PasswordResetConfirmView.as_view()),
]
