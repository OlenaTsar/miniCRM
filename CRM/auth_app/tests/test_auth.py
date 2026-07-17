import pytest

from auth_app.tests.factories import UserFactory
from auth_app.models import User


@pytest.mark.django_db
class TestRegister:
    def test_register_success(self, api_client):
        res = api_client.post("/api/auth/register/", {
            "email": "new@test.com",
            "password": "pass12345",
            "first_name": "Test",
            "last_name": "User"
        })
        assert res.status_code == 201

    def test_register_invalid_email(self, api_client):
        res = api_client.post("/api/auth/register/", {
            "email": "invalid_email",
            "password": "pass12345",
            "first_name": "Test",
            "last_name": "User"
        })
        assert res.status_code == 400

    def test_register_short_password(self, api_client):
        res = api_client.post("/api/auth/register/", {
            "email": "new@test.com",
            "password": "short",
            "first_name": "Test",
            "last_name": "User"
        })
        assert res.status_code == 400

    def test_register_duplicate_email(self, api_client):
        UserFactory(email="existing@test.com")
        res = api_client.post("/api/auth/register/", {
            "email": "existing@test.com",
            "password": "pass12345",
            "first_name": "Test",
            "last_name": "User"
        })
        assert res.status_code == 400

    def test_register_without_required_fields(self, api_client):
        res = api_client.post("/api/auth/register/", {
            "password": "pass12345",
            "first_name": "Test",
            "last_name": "User"
        })
        assert res.status_code == 400
        res = api_client.post("/api/auth/register/", {
            "email": "new@test.com",
            "first_name": "Test",
            "last_name": "User"
        })
        assert res.status_code == 400
        res = api_client.post("/api/auth/register/", {
            "email": "new@test.com",
            "password": "pass12345",
            "last_name": "User"
        })
        assert res.status_code == 400
        res = api_client.post("/api/auth/register/", {
            "email": "new@test.com",
            "password": "pass12345",
            "first_name": "Test",
        })
        assert res.status_code == 400

    def test_register_with_invalid_data(self, api_client):
        # спроба передати при реєстрації role, is_verified, is_staff
        res = api_client.post("/api/auth/register/", {
            "email": "new@test.com",
            "password": "pass12345",
            "first_name": "Test",
            "last_name": "User",
            "role": 'admin',
            "is_verified": True,
            "is_staff": True
        })
        assert res.status_code == 201
        user = User.objects.get(email="new@test.com")
        assert user.role == "employee"
        assert user.is_verified is False
        assert user.is_staff is False


@pytest.mark.django_db
class TestVerifyEmail:
    def test_verify_email_success(self, api_client):
        # перевіряє, чи генерується токен при реєстрації, і верифікацію
        api_client.post("/api/auth/register/", {
            "email": "test@test.com",
            "password": "pass12345",
            "first_name": "Test",
            "last_name": "User"
        })
        user = User.objects.get(email="test@test.com")
        assert user.email_verification_token is not None
        res = api_client.get(f"/api/auth/verify-email/{user.email_verification_token}/")
        assert res.status_code == 200
        user.refresh_from_db()
        assert user.is_verified is True

    def test_verify_email_invalid_token(self, api_client):
        res = api_client.get("/api/auth/verify-email/00000000-0000-0000-0000-000000000000/")
        assert res.status_code == 400


@pytest.mark.django_db
class TestLogin:
    def test_login_success(self, api_client):
        user = UserFactory(is_verified=True, is_active=True)
        res = api_client.post("/api/auth/login/", {
            "email": user.email,
            "password": "pass12345",
        })
        assert res.status_code == 200
        assert "access" in res.data
        assert "refresh" in res.data

    def test_login_not_verified(self, api_client):
        user = UserFactory(is_verified=False)
        res = api_client.post("/api/auth/login/", {
            "email": user.email,
            "password": "pass12345",
        })
        assert res.status_code == 403

    def test_login_not_active(self, api_client):
        user = UserFactory(is_active=False, is_verified=True)
        res = api_client.post("/api/auth/login/", {
            "email": user.email,
            "password": "pass12345",
        })
        assert res.status_code == 403

    def test_login_wrong_password(self, api_client):
        user = UserFactory(is_verified=True)
        res = api_client.post("/api/auth/login/", {
            "email": user.email,
            "password": "wrongpass",
        })
        assert res.status_code == 401


@pytest.mark.django_db
class TestLogout:
    def test_logout_success(self, api_client):
        user = UserFactory(is_verified=True)
        login_res = api_client.post("/api/auth/login/", {
            "email": user.email,
            "password": "pass12345",
        })
        refresh_token = login_res.data["refresh"]
        access_token = login_res.data["access"]

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        res = api_client.post("/api/auth/logout/", {"refresh": refresh_token})
        assert res.status_code == 200

        # перевірка що refresh_token більше не працює
        res = api_client.post("/api/auth/token/refresh/", {"refresh": refresh_token})
        assert res.status_code == 401

    def test_logout_invalid_token(self, api_client, manager_user):
        api_client.force_authenticate(user=manager_user)
        res = api_client.post("/api/auth/logout/", {"refresh": "invalid_token"})
        assert res.status_code == 400


@pytest.mark.django_db
class TestPasswordReset:
    def test_password_reset_request(self, api_client):
        user = UserFactory(is_verified=True)
        res = api_client.post("/api/auth/password-reset/", {"email": user.email})
        assert res.status_code == 200
        user.refresh_from_db()
        assert user.password_reset_token is not None

    def test_password_reset_nonexistent_email(self, api_client):
        # не повідомляємо про неіснуючий email
        res = api_client.post("/api/auth/password-reset/", {
            "email": "nonexistent@test.com"
        })
        assert res.status_code == 200

    def test_password_reset_confirm_success(self, api_client):
        user = UserFactory(is_verified=True)
        user.generate_password_reset_token()

        res = api_client.post(
            f"/api/auth/password-reset/confirm/{user.password_reset_token}/",
            {"new_password": "newpass123"}
        )
        assert res.status_code == 200

        # новий пароль працює
        login_res = api_client.post("/api/auth/login/", {
            "email": user.email,
            "password": "newpass123",
        })
        assert login_res.status_code == 200

    def test_password_reset_confirm_expired_token(self, api_client):
        from django.utils import timezone
        from datetime import timedelta

        user = UserFactory(is_verified=True)
        user.generate_password_reset_token()
        user.password_reset_token_expires = timezone.now() - timedelta(hours=2)
        user.save()

        res = api_client.post(
            f"/api/auth/password-reset/confirm/{user.password_reset_token}/",
            {"new_password": "newpass123"}
        )
        assert res.status_code == 400
