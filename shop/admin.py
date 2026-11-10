from django.contrib import admin

from .models import Category, Order, OrderItem, Product, ProductRating


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    actions = ('delete_selected',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock', 'is_available', 'created_at')
    list_filter = ('category', 'is_available', 'created_at')
    actions = ('delete_selected',)
    list_editable = ('price', 'stock', 'is_available')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')


@admin.register(ProductRating)
class ProductRatingAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'score', 'updated_at')
    list_filter = ('score', 'updated_at')
    search_fields = ('product__name', 'user__username')
    readonly_fields = ('updated_at',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'price', 'quantity')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'phone', 'status', 'total', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'phone', 'address')
    readonly_fields = ('user', 'phone', 'address', 'total', 'created_at')
    inlines = (OrderItemInline,)
