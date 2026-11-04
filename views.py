from django.shortcuts import render, get_object_or_404

from .models import Category, Product


def home(request):
    categories = Category.objects.all()
    products = Product.objects.filter(is_available=True)[:8]
    return render(request, 'shop/home.html', {
        'categories': categories,
        'products': products,
    })


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(is_available=True)

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    return render(request, 'shop/product_list.html', {
        'category': category,
        'categories': categories,
        'products': products,
    })


def product_detail(request, category_slug, product_slug):
    product = get_object_or_404(
        Product,
        category__slug=category_slug,
        slug=product_slug,
    )
    return render(request, 'shop/product_detail.html', {
        'product': product,
    })


def cart_summary(request):
    from .cart import Cart
    return render(request, 'shop/cart_summary.html', {
        'cart': Cart(request),
    })
