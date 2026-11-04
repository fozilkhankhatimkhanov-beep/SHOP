from django.test import TestCase
from django.contrib.auth.models import User


class AuthFlowTest(TestCase):
    def test_register_user_creates_account_and_logs_in(self):
        response = self.client.get("/auth/register/")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/auth/register/",
            {"username": "testuser", "email": "test@example.com",
             "password": "StrongPass123", "password2": "StrongPass123"},
            follow=True,
        )
        self.assertTrue(
            User.objects.filter(username="testuser").exists()
        )
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_remember_checkbox_controls_session_expiry(self):
        user = User.objects.create_user(username="remember", password="StrongPass123")

        response = self.client.post(
            "/auth/login/",
            {"username": user.username, "password": "StrongPass123"},
            follow=True,
        )

        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertTrue(self.client.session.get_expire_at_browser_close())

        self.client.post("/auth/logout/")
        response = self.client.post(
            "/auth/login/",
            {
                "username": user.username,
                "password": "StrongPass123",
                "remember": "on",
            },
            follow=True,
        )

        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertFalse(self.client.session.get_expire_at_browser_close())
