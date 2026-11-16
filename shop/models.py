from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .pricing import CARD_DISCOUNT_THRESHOLD, discounted_card_price

ORDER_CANCELLATION_WINDOW = timedelta(minutes=30)


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

    @property
    def card_price(self):
        return discounted_card_price(self.price)

    @property
    def has_card_discount(self):
        return self.price >= CARD_DISCOUNT_THRESHOLD


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


class SavedPaymentCard(models.Model):
    class Brand(models.TextChoices):
        UZCARD = 'uzcard', 'Uzcard'
        HUMO = 'humo', 'Humo'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='saved_payment_cards',
        on_delete=models.CASCADE,
    )
    brand = models.CharField(max_length=8, choices=Brand.choices)
    last_four = models.CharField(
        max_length=4,
        validators=[RegexValidator(r'^\d{4}$')],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.get_brand_display()} •••• {self.last_four}'


class Order(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'Naqd pul'
        CARD = 'card', 'Plastik karta'

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
    payment_method = models.CharField(
        max_length=8,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    @property
    def can_be_canceled(self):
        return (
            self.status == self.Status.PENDING
            and timezone.now() < self.created_at + ORDER_CANCELLATION_WINDOW
        )

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
