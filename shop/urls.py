from django.urls import path
from . import views
from . import cart

app_name = 'shop'

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('shop/', views.product_list, name='product_list'),
    path('shop/<slug:category_slug>/<slug:product_slug>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_summary, name='cart_summary'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_history, name='order_history'),
    path('orders/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('orders/<int:order_id>/success/', views.order_success, name='order_success'),
    path('products/<int:product_id>/rate/', views.rate_product, name='rate_product'),
    path('cart/add/<int:product_id>/', cart.cart_add, name='cart_add'),
    path('cart/update/<int:product_id>/', cart.cart_update, name='cart_update'),
    path('cart/remove/<int:product_id>/', cart.cart_remove, name='cart_remove'),
    path('cart/clear/', cart.cart_clear, name='cart_clear'),
]
