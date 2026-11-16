import base64
from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
import qrcode
from qrcode.image.svg import SvgPathImage

from .cart import Cart
from .forms import CheckoutForm
from .models import (
    ORDER_CANCELLATION_WINDOW,
    Category,
    Order,
    OrderItem,
    Product,
    ProductRating,
    SavedPaymentCard,
)
from .pricing import discounted_card_price


def _rated_products():
    return Product.objects.annotate(
        average_rating=Avg('ratings__score'),
        rating_count=Count('ratings'),
    )


@login_required(login_url='shop_auth:login')
def home(request):
    categories = Category.objects.all()
    products = _rated_products().filter(is_available=True)[:8]
    return render(request, 'shop/home.html', {
        'categories': categories,
        'products': products,
    })


@login_required(login_url='shop_auth:login')
def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = _rated_products().filter(is_available=True)
    query = request.GET.get('q', '').strip()

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    for term in query.split():
        products = products.filter(
            Q(name__icontains=term)
            | Q(slug__icontains=term)
            | Q(description__icontains=term)
            | Q(category__name__icontains=term)
            | Q(category__slug__icontains=term)
        )

    return render(request, 'shop/product_list.html', {
        'category': category,
        'categories': categories,
        'products': products,
        'query': query,
    })


@login_required(login_url='shop_auth:login')
def product_detail(request, category_slug, product_slug):
    product = get_object_or_404(
        _rated_products(),
        category__slug=category_slug,
        slug=product_slug,
    )
    user_rating = ProductRating.objects.filter(
        product=product,
        user=request.user,
    ).first()
    return render(request, 'shop/product_detail.html', {
        'product': product,
        'user_rating': user_rating,
    })


@login_required(login_url='shop_auth:login')
def cart_summary(request):
    return render(request, 'shop/cart_summary.html', {
        'cart': Cart(request),
    })


@login_required(login_url='shop_auth:login')
@require_POST
def add_saved_payment_card(request):
    brand = request.POST.get('brand', '')
    last_four = request.POST.get('last_four', '')
    if (
        brand not in SavedPaymentCard.Brand.values
        or len(last_four) != 4
        or not last_four.isascii()
        or not last_four.isdigit()
    ):
        return JsonResponse(
            {'success': False, 'error': 'Karta ma’lumotlari noto‘g‘ri.'},
            status=400,
        )

    card = SavedPaymentCard.objects.filter(
        user=request.user,
        brand=brand,
        last_four=last_four,
    ).first()
    if card is None:
        card = SavedPaymentCard.objects.create(
            user=request.user,
            brand=brand,
            last_four=last_four,
        )

    return JsonResponse({
        'success': True,
        'card': {
            'brand': card.get_brand_display(),
            'last_four': card.last_four,
        },
    })


@login_required(login_url='shop_auth:login')
def checkout(request):
    cart = Cart(request)
    saved_cards = request.user.saved_payment_cards.all()
    form = CheckoutForm(request.POST or None)
    if not cart.cart:
        messages.error(request, 'Buyurtma berish uchun savatga mahsulot qo‘shing.')
        return redirect('shop:cart_summary')

    if request.method == 'POST' and form.is_valid():
        payment_method = form.cleaned_data['payment_method']
        if (
            payment_method == Order.PaymentMethod.CARD
            and not saved_cards.exists()
        ):
            form.add_error(
                'payment_method',
                'Plastik karta bilan buyurtma berish uchun avval karta qo‘shing.',
            )
            return render(request, 'shop/checkout.html', {
                'cart': cart,
                'form': form,
                'saved_cards': saved_cards,
            })

        try:
            requested_quantities = {
                int(product_id): int(item['quantity'])
                for product_id, item in cart.cart.items()
            }
        except (KeyError, TypeError, ValueError):
            messages.error(request, 'Savat ma’lumotlari noto‘g‘ri. Savatni tekshiring.')
            return redirect('shop:cart_summary')

        if any(quantity < 1 for quantity in requested_quantities.values()):
            messages.error(request, 'Mahsulot miqdori noto‘g‘ri. Savatni tekshiring.')
            return redirect('shop:cart_summary')

        with transaction.atomic():
            products = list(
                Product.objects.select_for_update().filter(
                    id__in=requested_quantities,
                )
            )
            products_by_id = {product.id: product for product in products}

            if len(products_by_id) != len(requested_quantities):
                messages.error(
                    request,
                    'Savatdagi ayrim mahsulotlar endi mavjud emas. Savatni yangilang.',
                )
                return redirect('shop:cart_summary')

            unavailable = [
                product.name
                for product_id, product in products_by_id.items()
                if (
                    not product.is_available
                    or product.stock < requested_quantities[product_id]
                )
            ]
            if unavailable:
                messages.error(
                    request,
                    'Omborda yetarli mahsulot yo‘q: ' + ', '.join(unavailable),
                )
                return render(request, 'shop/checkout.html', {
                    'cart': cart,
                    'form': form,
                    'saved_cards': saved_cards,
                })

            unit_prices = {
                product_id: (
                    discounted_card_price(product.price)
                    if payment_method == Order.PaymentMethod.CARD
                    else product.price
                )
                for product_id, product in products_by_id.items()
            }
            order_total = sum(
                (
                    unit_prices[product_id] * requested_quantities[product_id]
                    for product_id in products_by_id
                ),
                Decimal('0.00'),
            )
            order = Order.objects.create(
                user=request.user,
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address'],
                payment_method=payment_method,
                total=order_total,
            )
            OrderItem.objects.bulk_create([
                OrderItem(
                    order=order,
                    product=product,
                    product_name=product.name,
                    price=unit_prices[product_id],
                    quantity=requested_quantities[product_id],
                )
                for product_id, product in products_by_id.items()
            ])

            for product_id, product in products_by_id.items():
                product.stock -= requested_quantities[product_id]
                product.save(update_fields=('stock', 'updated_at'))

        cart.clear()
        return redirect('shop:order_success', order_id=order.pk)

    return render(request, 'shop/checkout.html', {
        'cart': cart,
        'form': form,
        'saved_cards': saved_cards,
    })


@login_required(login_url='shop_auth:login')
def order_success(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        pk=order_id,
        user=request.user,
    )
    receipt_lines = [
        f'Buyurtma #{order.pk}',
        f'Sana: {order.created_at:%d.%m.%Y %H:%M}',
    ]
    receipt_lines.extend(
        f'{item.product_name} x {item.quantity}'
        for item in order.items.all()
    )
    receipt_lines.append(f'Jami: {order.total} so\'m')

    qr_image = qrcode.make(
        '\n'.join(receipt_lines),
        image_factory=SvgPathImage,
        box_size=6,
        border=2,
    )
    qr_buffer = BytesIO()
    qr_image.save(qr_buffer)
    qr_code_data = base64.b64encode(qr_buffer.getvalue()).decode('ascii')

    return render(request, 'shop/order_success.html', {
        'order': order,
        'qr_code_data': qr_code_data,
    })


@login_required(login_url='shop_auth:login')
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'shop/order_history.html', {'orders': orders})


@login_required(login_url='shop_auth:login')
@require_POST
def cancel_order(request, order_id):
    with transaction.atomic():
        order = get_object_or_404(
            Order.objects.select_for_update(),
            pk=order_id,
            user=request.user,
        )
        if order.status != Order.Status.PENDING:
            messages.error(request, 'Faqat kutilayotgan buyurtmani bekor qilish mumkin.')
        elif timezone.now() >= order.created_at + ORDER_CANCELLATION_WINDOW:
            messages.error(request, 'Buyurtmani bekor qilish uchun 30 daqiqa o‘tib ketgan.')
        else:
            items = list(
                OrderItem.objects.filter(order=order).values(
                    'product_id',
                    'quantity',
                )
            )
            products = Product.objects.select_for_update().in_bulk(
                item['product_id'] for item in items if item['product_id'] is not None
            )
            for item in items:
                product = products.get(item['product_id'])
                if product is not None:
                    product.stock += item['quantity']
                    product.save(update_fields=('stock', 'updated_at'))

            order.status = Order.Status.CANCELED
            order.save(update_fields=('status',))
            messages.success(request, 'Buyurtma bekor qilindi.')

    return redirect('shop:order_history')


@login_required(login_url='shop_auth:login')
@require_POST
def rate_product(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    try:
        score = int(request.POST.get('score', ''))
    except (TypeError, ValueError):
        messages.error(request, 'Bahoni 1 dan 15 gacha tanlang.')
        return redirect(
            'shop:product_detail',
            category_slug=product.category.slug,
            product_slug=product.slug,
        )

    if not 1 <= score <= 15:
        messages.error(request, 'Baho 1 dan 15 gacha bo‘lishi kerak.')
    else:
        ProductRating.objects.update_or_create(
            product=product,
            user=request.user,
            defaults={'score': score},
        )
        messages.success(request, 'Mahsulot bahosi saqlandi.')

    return redirect(
        'shop:product_detail',
        category_slug=product.category.slug,
        product_slug=product.slug,
    )
