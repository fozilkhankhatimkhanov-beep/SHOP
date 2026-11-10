from shop.cart import Cart


def cart(request):
    current_cart = Cart(request)
    return {
        'cart': current_cart,
        'cart_product_ids': list(current_cart.cart.keys()),
        'cart_product_quantities': {
            product_id: item['quantity']
            for product_id, item in current_cart.cart.items()
        },
    }


def auth_urls(request):
    return {
        'login_url': '/auth/login/',
        'logout_url': '/auth/logout/',
        'register_url': '/auth/register/',
    }
