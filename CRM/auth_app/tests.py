from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthFlowTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register(self):
        res = self.client.post("/api/auth/register/", {
            "email": "user@test.com",
            "password": "pass12345",
            "first_name": "Test",
            "last_name": "Test"
        })
        self.assertEqual(res.status_code, 201)
        self.assertFalse(User.objects.get(email="user@test.com").is_verified)

    def test_login_before_verification(self):
        User.objects.create_user(email="x@test.com", password="pass12345")
        res = self.client.post("/api/auth/login/", {
            "email": "x@test.com", "password": "pass12345"
        })
        self.assertEqual(res.status_code, 403)

    def test_full_flow(self):
        # реєстрація
        self.client.post("/api/auth/register/", {
            "email": "full@test.com",
            "password": "pass12345",
            "first_name": "Test",
            "last_name": "Test"
        })
        user = User.objects.get(email="full@test.com")

        # верифікація
        res = self.client.get(f"/api/auth/verify-email/{user.email_verification_token}/")
        self.assertEqual(res.status_code, 200)

        # login
        res = self.client.post("/api/auth/login/", {
            "email": "full@test.com", "password": "pass12345"
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)

    def test_login_not_active_account(self):
        # реєстрація
        self.client.post("/api/auth/register/", {
            "email": "user@test.com",
            "password": "pass12345",
            "first_name": "Test",
            "last_name": "Test"
        })
        user = User.objects.get(email="user@test.com")

        # верифікація
        self.client.get(f"/api/auth/verify-email/{user.email_verification_token}/")

        # деактивація акаунту
        user.is_active = False
        user.save()

        # login
        res = self.client.post("/api/auth/login/", {
            "email": "user@test.com", "password": "pass12345"
        })
        self.assertEqual(res.status_code, 403)

    def test_register_with_invalid_data(self):
        email = "user@test.com"
        password = "pass12345"
        first_name = "Test"
        last_name = "Test"

        # реєстрація з некоректним email
        res = self.client.post("/api/auth/register/", {
            "email": "incorrect_email",
            "password": password,
            "first_name": first_name,
            "last_name": last_name
        })
        self.assertEqual(res.status_code, 400)
        self.assertFalse(User.objects.filter(email="incorrect_email").exists())

        # реєстрація з некоректним password
        res = self.client.post("/api/auth/register/", {
            "email": email,
            "password": 'short',
            "first_name": first_name,
            "last_name": last_name
        })
        self.assertEqual(res.status_code, 400)
        self.assertFalse(User.objects.filter(email=email).exists())

        # спроба передати при реєстрації role, is_verified, is_staff
        res = self.client.post("/api/auth/register/", {
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "role": 'admin',
            "is_verified": True,
            "is_staff": True
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(User.objects.get(email=email).role, 'employee')
        self.assertFalse(User.objects.get(email=email).is_verified)
        self.assertFalse(User.objects.get(email=email).is_staff)
