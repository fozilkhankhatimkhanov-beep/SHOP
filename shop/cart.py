from decimal import Decimal
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from .models import Product


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, override_quantity=False):
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0,
                'price': str(product.price),
            }
        if override_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
        self.save()

    def save(self):
        self.session.modified = True

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        product_ids = list(self.cart.keys())
        products = Product.objects.filter(id__in=product_ids)
        cart = {
            product_id: item.copy()
            for product_id, item in self.cart.items()
        }
        price_changed = False
        for product in products:
            product_id = str(product.id)
            current_price = str(product.price)
            if self.cart[product_id].get('price') != current_price:
                self.cart[product_id]['price'] = current_price
                price_changed = True
            cart[product_id]['product'] = product
        if price_changed:
            self.save()

        for item in cart.values():
            if 'product' not in item:
                continue
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        products = Product.objects.in_bulk(self.cart.keys())
        total = Decimal('0.00')
        price_changed = False
        for product_id, item in self.cart.items():
            product = products.get(int(product_id))
            if product is not None:
                current_price = str(product.price)
                if item.get('price') != current_price:
                    item['price'] = current_price
                    price_changed = True
                total += product.price * item['quantity']
        if price_changed:
            self.save()
        return total

    def clear(self):
        self.session[settings.CART_SESSION_ID] = {}
        self.save()


def _get_cart_quantity(request):
    try:
        quantity = int(request.POST.get('quantity', '1'))
    except (TypeError, ValueError):
        return None
    return quantity if quantity > 0 else None


@require_POST
@login_required(login_url='shop_auth:login')
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = _get_cart_quantity(request)
    if quantity is None:
        return JsonResponse({'success': False, 'error': 'Miqdor noto‘g‘ri.'}, status=400)
    if not product.is_available or product.stock < 1:
        return JsonResponse({'success': False, 'error': 'Mahsulot mavjud emas.'}, status=400)

    cart = Cart(request)
    current_quantity = cart.cart.get(str(product.id), {}).get('quantity', 0)
    if current_quantity + quantity > product.stock:
        return JsonResponse({'success': False, 'error': 'Omborda yetarli mahsulot yo‘q.'}, status=400)

    cart.add(product=product, quantity=quantity)
    return JsonResponse({'success': True, 'cart_count': len(cart)})


@require_POST
@login_required(login_url='shop_auth:login')
def cart_update(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = _get_cart_quantity(request)
    if quantity is None:
        return JsonResponse({'success': False, 'error': 'Miqdor noto‘g‘ri.'}, status=400)
    if not product.is_available or quantity > product.stock:
        return JsonResponse({'success': False, 'error': 'Omborda yetarli mahsulot yo‘q.'}, status=400)

    cart = Cart(request)
    cart.add(product=product, quantity=quantity, override_quantity=True)
    return JsonResponse({'success': True, 'cart_count': len(cart)})


@require_POST
@login_required(login_url='shop_auth:login')
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return JsonResponse({'success': True, 'cart_count': len(cart)})


@require_POST
@login_required(login_url='shop_auth:login')
def cart_clear(request):
    cart = Cart(request)
    cart.clear()
    return JsonResponse({'success': True, 'cart_count': 0})
