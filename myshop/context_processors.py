from shop.cart import Cart


def cart(request):
    return {'cart': Cart(request)}


def auth_urls(request):
    return {
        'login_url': '/auth/login/',
        'logout_url': '/auth/logout/',
        'register_url': '/auth/register/',
    }
