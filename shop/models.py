from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return self.name


class ProductRating(models.Model):
    product = models.ForeignKey(
        Product,
        related_name='ratings',
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='product_ratings',
        on_delete=models.CASCADE,
    )
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(15)],
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('product', 'user'),
                name='unique_rating_per_user_product',
            ),
            models.CheckConstraint(
                condition=Q(score__gte=1) & Q(score__lte=15),
                name='product_rating_score_1_to_15',
            ),
        ]
        ordering = ('-updated_at',)

    def __str__(self):
        return f'{self.user} rated {self.product}: {self.score}/15'


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Kutilmoqda'
        CONFIRMED = 'confirmed', 'Tasdiqlangan'
        SHIPPED = 'shipped', 'Yetkazilmoqda'
        DELIVERED = 'delivered', 'Yetkazildi'
        CANCELED = 'canceled', 'Bekor qilindi'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='shop_orders',
        on_delete=models.PROTECT,
    )
    phone = models.CharField(max_length=32)
    address = models.TextField()
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'Buyurtma #{self.pk} — {self.user}'


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        related_name='order_items',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    product_name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.product_name} × {self.quantity}'
