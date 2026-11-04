from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages


def register(request):
    if request.user.is_authenticated:
        return redirect('shop:home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        if not username:
            messages.error(request, 'Username kiriting.')
        elif not password or len(password) < 8:
            messages.error(request, 'Parol kamida 8 belgidan iborat bo\'lsin.')
        elif password != password2:
            messages.error(request, 'Parollar mos kelmadi.')
        else:
            if authenticate(username=username):
                messages.error(request, 'Bu username band.')
            else:
                user = authenticate(
                    username=username,
                    password=password,
                ) or None
                if user is None:
                    from django.contrib.auth.models import User
                    user = User.objects.create_user(
                        username=username,
                        email=email or '',
                        password=password,
                    )
                login(request, user)
                messages.success(request, 'Muvaffaqiyatli ro\'yhatdan o\'tdingiz!')
                return redirect('shop:home')
        return redirect('shop_auth:register')

    return render(request, 'shop_auth/register.html')
