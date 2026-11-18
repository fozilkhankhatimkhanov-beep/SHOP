from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse


class AuthFlowTest(TestCase):
    def test_login_page_links_to_admin_panel(self):
        response = self.client.get(reverse('shop_auth:login'))

        self.assertContains(
            response,
            '<a href="/admin/" class="btn btn-ghost btn-small">Admin</a>',
        )

    def test_register_user_creates_account_and_logs_in(self):
        response = self.client.get("/auth/register/")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/auth/register/",
            {"username": "testuser", "email": "test@example.com",
             "password": "StrongPass123", "password2": "StrongPass123"},
            follow=True,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertTrue(
            User.objects.filter(username="testuser").exists()
        )
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertContains(response, "Yaxshi tanlov.")
        self.assertRegex(
            response.content.decode(),
            r"site(?:\.[0-9a-f]{12})?\.js\?v=4",
        )

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

    def test_authenticated_user_can_change_password_without_email(self):
        user = User.objects.create_user(
            username='change-password',
            password='OriginalStrong123!',
        )
        login_page = self.client.get(reverse('shop_auth:login'))
        self.assertContains(login_page, 'Parolni o‘zgartirish')
        self.assertContains(login_page, 'password-change-button')
        self.assertContains(
            login_page,
            reverse('shop_auth:password_change'),
        )

        self.assertRedirects(
            self.client.get(reverse('shop_auth:password_change')),
            f"{reverse('shop_auth:login')}?next={reverse('shop_auth:password_change')}",
        )
        self.client.force_login(user)
        change_url = reverse('shop_auth:password_change')
        self.assertContains(
            self.client.get(change_url),
            'Joriy parol',
        )

        response = self.client.post(
            change_url,
            {
                'old_password': 'WrongPassword123!',
                'new_password1': 'NewStrongPassword456!',
                'new_password2': 'NewStrongPassword456!',
            },
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password('OriginalStrong123!'))

        response = self.client.post(
            change_url,
            {
                'old_password': 'OriginalStrong123!',
                'new_password1': 'NewStrongPassword456!',
                'new_password2': 'NewStrongPassword456!',
            },
        )
        self.assertRedirects(
            response,
            reverse('shop_auth:password_change_done'),
        )
        user.refresh_from_db()
        self.assertTrue(user.check_password('NewStrongPassword456!'))
