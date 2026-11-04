from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


def _auth_redirect_target(request):
    target = request.POST.get('next') or request.GET.get('next')
    if target and url_has_allowed_host_and_scheme(
        target,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return target
    return reverse('shop:home')


def _render_auth_page(request, template_name):
    return render(request, template_name, {
        'next_url': request.POST.get('next') or request.GET.get('next', ''),
    })


def register(request):
    if request.user.is_authenticated:
        return redirect(_auth_redirect_target(request))

    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        email = (request.POST.get('email') or '').strip()
        password = request.POST.get('password') or ''
        password2 = request.POST.get('password2') or ''

        if not username:
            messages.error(request, 'Username kiriting.')
        elif len(password) < 8:
            messages.error(request, "Parol kamida 8 belgidan iborat bo'lishi kerak.")
        elif password != password2:
            messages.error(request, 'Parollar mos kelmadi.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Bu username band.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            messages.success(request, "Muvaffaqiyatli ro'yxatdan o'tdingiz!")
            return redirect(_auth_redirect_target(request))

        return _render_auth_page(request, 'shop_auth/register.html')

    return _render_auth_page(request, 'shop_auth/register.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect(_auth_redirect_target(request))

    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            request.session.set_expiry(
                None if request.POST.get('remember') else 0
            )
            messages.success(request, 'Muvaffaqiyatli kirdingiz.')
            return redirect(_auth_redirect_target(request))

        messages.error(request, 'Username yoki parol noto\'g\'ri.')
        return _render_auth_page(request, 'shop_auth/login.html')

    return _render_auth_page(request, 'shop_auth/login.html')


def logout_view(request):
    if request.method == 'POST':
        logout(request)
    return redirect(reverse('shop:home'))
