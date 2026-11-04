from django.urls import path
from . import views
from . import cart

app_name = 'shop'

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.product_list, name='product_list'),
    path('shop/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('shop/<slug:category_slug>/<slug:product_slug>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_summary, name='cart_summary'),
    path('cart/add/<int:product_id>/', cart.cart_add, name='cart_add'),
    path('cart/remove/<int:product_id>/', cart.cart_remove, name='cart_remove'),
    path('cart/clear/', cart.cart_clear, name='cart_clear'),
]
