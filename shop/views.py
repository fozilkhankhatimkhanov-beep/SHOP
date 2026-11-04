from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .cart import Cart
from .forms import CheckoutForm
from .models import Category, Order, OrderItem, Product, ProductRating


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

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
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
def checkout(request):
    cart = Cart(request)
    form = CheckoutForm(request.POST or None)
    if not cart.cart:
        messages.error(request, 'Buyurtma berish uchun savatga mahsulot qo‘shing.')
        return redirect('shop:cart_summary')

    if request.method == 'POST' and form.is_valid():
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
                })

            order_total = sum(
                (
                    product.price * requested_quantities[product_id]
                    for product_id, product in products_by_id.items()
                ),
                Decimal('0.00'),
            )
            order = Order.objects.create(
                user=request.user,
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address'],
                total=order_total,
            )
            OrderItem.objects.bulk_create([
                OrderItem(
                    order=order,
                    product=product,
                    product_name=product.name,
                    price=product.price,
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
    })


@login_required(login_url='shop_auth:login')
def order_success(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        pk=order_id,
        user=request.user,
    )
    return render(request, 'shop/order_success.html', {'order': order})


@login_required(login_url='shop_auth:login')
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'shop/order_history.html', {'orders': orders})


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
