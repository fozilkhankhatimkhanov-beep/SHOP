import base64
from datetime import timedelta
from unittest.mock import patch

import qrcode
import tempfile

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal

from shop.models import (
    Category,
    Order,
    OrderItem,
    Product,
    ProductRating,
    SavedPaymentCard,
)


class CategoryModelTest(TestCase):
    def test_create_category_with_slug(self):
        category = Category.objects.create(
            name="Kitoblar",
            slug="kitoblar",
        )
        category.refresh_from_db()
        self.assertEqual(category.name, "Kitoblar")
        self.assertEqual(category.slug, "kitoblar")

    def test_category_str(self):
        category = Category.objects.create(name="Elektronika")
        self.assertEqual(str(category), "Elektronika")


class ProductModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Oyinchoqlar",
            slug="oyinchoqlar",
        )

    def test_create_product_defaults(self):
        product = Product.objects.create(
            category=self.category,
            name="Lego Set",
            slug="lego-set",
            price=Decimal("1200000.00"),
        )
        product.refresh_from_db()
        self.assertEqual(product.stock, 0)
        self.assertTrue(product.is_available)
        self.assertEqual(str(product), "Lego Set")
        self.assertEqual(product.card_price, Decimal("1140000.00"))
        self.assertTrue(product.has_card_discount)

    def test_card_discount_starts_at_twenty_thousand_soums(self):
        below_threshold = Product.objects.create(
            category=self.category,
            name="Cheap toy",
            slug="cheap-toy",
            price=Decimal("19999.00"),
        )
        at_threshold = Product.objects.create(
            category=self.category,
            name="Eligible toy",
            slug="eligible-toy",
            price=Decimal("20000.00"),
        )

        self.assertEqual(below_threshold.card_price, Decimal("19999.00"))
        self.assertFalse(below_threshold.has_card_discount)
        self.assertEqual(at_threshold.card_price, Decimal("19000.00"))
        self.assertTrue(at_threshold.has_card_discount)

    def test_available_products_filter(self):
        Product.objects.create(
            category=self.category,
            name="Out of stock toy",
            slug="oos-toy",
            price=Decimal("100000.00"),
            stock=0,
            is_available=False,
        )
        Product.objects.create(
            category=self.category,
            name="In stock toy",
            slug="is-toy",
            price=Decimal("100000.00"),
            stock=5,
            is_available=True,
        )
        available = Product.objects.filter(is_available=True)
        self.assertEqual(available.count(), 1)
        self.assertEqual(available.first().name, "In stock toy")


class CatalogSeedTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="catalog-user", password="StrongPass123")
        self.client.force_login(user)
        self.media_directory = tempfile.TemporaryDirectory()
        self.media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.media_settings.enable()
        self.addCleanup(self.media_settings.disable)
        self.addCleanup(self.media_directory.cleanup)

    def test_seed_command_populates_catalog_idempotently(self):
        call_command("seed_data", verbosity=0, skip_photos=True)

        self.assertSetEqual(
            set(Category.objects.values_list("name", flat=True)),
            {
                "Elektronika",
                "Kiyim-kechak",
                "O'yinchoqlar",
                "Kitoblar",
                "Sport",
                "Idish-tovoqlar",
                "Uy-ro'zg'or",
                "Oshxona",
            },
        )
        self.assertEqual(Product.objects.count(), 41)
        self.assertFalse(Product.objects.filter(description="").exists())
        self.assertTrue(Product.objects.filter(name="Python darsligi").exists())
        self.assertTrue(Product.objects.filter(name="Sport shim").exists())
        self.assertTrue(Product.objects.filter(name="Simsiz quloqchin").exists())
        self.assertTrue(Product.objects.filter(name="Elektr choynak").exists())
        self.assertContains(self.client.get(reverse("shop:home")), "Kitoblar")
        self.assertContains(self.client.get(reverse("shop:home")), "Oshxona")
        self.assertContains(self.client.get(reverse("shop:product_list")), "Toster")

        call_command("seed_data", verbosity=0, skip_photos=True)
        self.assertEqual(Category.objects.count(), 8)
        self.assertEqual(Product.objects.count(), 41)


class ShopViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="shop-user",
            password="StrongPass123",
        )
        self.client.force_login(self.user)

    def test_home_page_status_and_context(self):
        response = self.client.get(reverse("shop:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Onlayn Bozor")
        self.assertContains(response, "site.js?v=4")
        self.assertRegex(
            response.content.decode(),
            r'<a href="/"[\r\n\s]+class="active" aria-current="page">Bosh sahifa',
        )
        self.assertIn("categories", response.context)
        self.assertIn("products", response.context)

    def test_navigation_exposes_order_history_and_admin_registers_catalog(self):
        response = self.client.get(reverse("shop:home"))
        self.assertContains(response, "Buyurtmalarim")
        self.assertContains(response, reverse("shop:order_history"))
        self.assertIn(Category, admin.site._registry)
        self.assertIn(Product, admin.site._registry)
        self.assertIn(Order, admin.site._registry)
        self.assertIn(ProductRating, admin.site._registry)

    def test_admin_can_delete_selected_categories(self):
        admin_user = User.objects.create_superuser(
            username="category-admin",
            password="test-password",
            email="admin@example.com",
        )
        Category.objects.create(name="Test category", slug="test-category")
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin:shop_category_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="delete_selected"')

    def test_cart_badge_only_appears_when_cart_has_products(self):
        response = self.client.get(reverse("shop:home"))
        self.assertNotContains(response, 'class="cart-count"')

        category = Category.objects.create(name="Kitoblar", slug="kitoblar")
        product = Product.objects.create(
            category=category,
            name="Python Darslik",
            slug="python-darslik",
            price=Decimal("150000.00"),
            stock=5,
        )
        self.client.post(reverse("shop:cart_add", args=[product.id]), {"quantity": 1})

        response = self.client.get(reverse("shop:home"))
        self.assertContains(response, '<span class="cart-count">1</span>', html=True)

    def test_guest_is_redirected_to_auth_and_sees_only_auth_navigation(self):
        self.client.logout()
        response = self.client.get(reverse("shop:home"), follow=True)

        self.assertEqual(response.redirect_chain[0][0], "/auth/login/?next=/")
        self.assertContains(response, reverse("shop_auth:register"))
        self.assertNotContains(response, 'href="/shop/"')
        self.assertNotContains(response, 'href="/cart/"')

    def test_product_list_page_status(self):
        response = self.client.get(reverse("shop:product_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Barcha mahsulotlar")
        self.assertRegex(
            response.content.decode(),
            r'<a href="/shop/"[\r\n\s]+class="active" aria-current="page">Mahsulotlar',
        )

    def test_product_pages_show_cash_and_discounted_card_prices(self):
        category = Category.objects.create(name="Kitoblar", slug="kitoblar")
        product = Product.objects.create(
            category=category,
            name="Python Darslik",
            slug="python-darslik",
            price=Decimal("20000.00"),
            stock=3,
        )

        list_response = self.client.get(reverse("shop:product_list"))
        detail_response = self.client.get(
            reverse(
                "shop:product_detail",
                kwargs={
                    "category_slug": category.slug,
                    "product_slug": product.slug,
                },
            )
        )

        for response in (list_response, detail_response):
            self.assertContains(response, "Naqd pul")
            self.assertContains(response, "Plastik karta")
            self.assertContains(response, "−5%")
            self.assertContains(response, "20 000 so&#x27;m")
            self.assertContains(response, "19 000 so&#x27;m")

    def test_carted_products_are_marked_on_catalog_and_detail_pages(self):
        category = Category.objects.create(name="Kitoblar", slug="kitoblar")
        product = Product.objects.create(
            category=category,
            name="Python Darslik",
            slug="python-darslik",
            price=Decimal("150000.00"),
            stock=3,
        )
        add_response = self.client.post(
            reverse("shop:cart_add", args=[product.id]),
            {"quantity": 2},
        )
        self.assertEqual(add_response.json()["product_quantity"], 2)

        list_response = self.client.get(reverse("shop:product_list"))
        detail_response = self.client.get(
            reverse("shop:product_detail", args=[category.slug, product.slug])
        )

        self.assertContains(list_response, 'class="add-to-cart-btn in-cart"')
        self.assertContains(list_response, "Savatda (2x) ✓")
        self.assertContains(detail_response, "Savatda (2x) ✓")
        self.assertContains(
            detail_response,
            'class="btn btn-primary btn-large in-cart"',
        )
        self.assertContains(detail_response, "product-detail.js?v=1")

    def test_product_search_filters_names_and_descriptions(self):
        category = Category.objects.create(name="Kitoblar", slug="kitoblar")
        Product.objects.create(
            category=category,
            name="Python Darslik",
            slug="python-darslik",
            price=Decimal("150000.00"),
            description="Dasturlashni o'rganish",
        )
        Product.objects.create(
            category=category,
            name="Matematika",
            slug="matematika",
            price=Decimal("120000.00"),
            description="Maktab uchun",
        )

        response = self.client.get(reverse("shop:product_list"), {"q": "python"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Darslik")
        self.assertNotContains(response, "Matematika")

    def test_product_search_matches_all_words_and_category_names(self):
        books = Category.objects.create(name="Kitoblar", slug="kitoblar")
        electronics = Category.objects.create(
            name="Elektronika",
            slug="elektronika",
        )
        Product.objects.create(
            category=books,
            name="Python Darslik",
            slug="python-darslik",
            price=Decimal("150000.00"),
            description="Dasturlashni o'rganish",
        )
        Product.objects.create(
            category=electronics,
            name="Simsiz Quloqchin",
            slug="simsiz-quloqchin",
            price=Decimal("250000.00"),
        )

        multi_word_response = self.client.get(
            reverse("shop:product_list"),
            {"q": "python dasturlash"},
        )
        category_response = self.client.get(
            reverse("shop:product_list"),
            {"q": "elektronika"},
        )

        self.assertContains(multi_word_response, "Python Darslik")
        self.assertNotContains(multi_word_response, "Simsiz Quloqchin")
        self.assertContains(category_response, "Simsiz Quloqchin")
        self.assertContains(category_response, "Qidiruv natijalari")

    def test_product_list_uses_slug_for_missing_product_image(self):
        category = Category.objects.create(name="Kitoblar", slug="kitoblar")
        Product.objects.create(
            category=category,
            name="Python Darslik",
            slug="python-darslik",
            price=Decimal("150000.00"),
            is_available=True,
        )

        response = self.client.get(reverse("shop:product_list"))

        self.assertContains(response, 'data-image="python-darslik.png"')

    def test_cart_summary_page_status(self):
        response = self.client.get(reverse("shop:cart_summary"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Savatingiz")

    def test_cart_quantity_uses_ajax_plus_minus_controls_without_typing(self):
        category = Category.objects.create(name="Kitoblar", slug="kitoblar")
        product = Product.objects.create(
            category=category,
            name="Python Darslik",
            slug="python-darslik",
            price=Decimal("150000.00"),
            stock=5,
        )
        self.client.post(
            reverse("shop:cart_add", args=[product.id]),
            {"quantity": 2},
        )

        response = self.client.get(reverse("shop:cart_summary"))

        self.assertContains(response, 'class="cart-qty-btn"')
        self.assertContains(response, 'data-action="decrease"')
        self.assertContains(response, 'data-action="increase"')
        self.assertContains(response, 'value="2"')
        self.assertContains(response, "readonly")

    def test_cart_add_and_update_enforce_stock_and_exact_quantity(self):
        category = Category.objects.create(name="Kitoblar", slug="kitoblar")
        product = Product.objects.create(
            category=category,
            name="Python Darslik",
            slug="python-darslik",
            price=Decimal("150000.00"),
            stock=5,
        )

        add_url = reverse("shop:cart_add", args=[product.id])
        update_url = reverse("shop:cart_update", args=[product.id])
        response = self.client.post(add_url, {"quantity": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cart_count"], 2)

        response = self.client.post(update_url, {"quantity": 4})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cart_count"], 4)

        response = self.client.post(update_url, {"quantity": 6})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.session["cart"][str(product.id)]["quantity"], 4)

    def test_cart_rejects_invalid_quantity_and_get_requests(self):
        category = Category.objects.create(name="Kitoblar", slug="kitoblar")
        product = Product.objects.create(
            category=category,
            name="Python Darslik",
            slug="python-darslik",
            price=Decimal("150000.00"),
            stock=5,
        )
        url = reverse("shop:cart_add", args=[product.id])

        self.assertEqual(self.client.post(url, {"quantity": "-1"}).status_code, 400)
        self.assertEqual(self.client.post(url, {"quantity": "abc"}).status_code, 400)
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_cart_page_provides_csrf_token_for_ajax(self):
        category = Category.objects.create(name="Kitoblar", slug="kitoblar")
        product = Product.objects.create(
            category=category,
            name="Python Darslik",
            slug="python-darslik",
            price=Decimal("150000.00"),
            stock=5,
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)

        page = client.get(reverse(
            "shop:product_detail",
            kwargs={"category_slug": category.slug, "product_slug": product.slug},
        ))
        self.assertEqual(page.status_code, 200)
        csrf_token = str(page.context["csrf_token"])
        response = client.post(
            reverse("shop:cart_add", args=[product.id]),
            {"quantity": 1},
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)

    def test_checkout_creates_order_and_decrements_stock(self):
        category = Category.objects.create(name="Kitoblar", slug="kitoblar")
        product = Product.objects.create(
            category=category,
            name="Python Darslik",
            slug="python-darslik",
            price=Decimal("150000.00"),
            stock=5,
        )
        self.client.post(reverse("shop:cart_add", args=[product.id]), {"quantity": 2})

        response = self.client.post(
            reverse("shop:checkout"),
            {
                "phone": "+998 90 123 45 67",
                "address": "Toshkent, Chilonzor, 12-uy",
            },
        )

        self.assertRedirects(
            response,
            reverse("shop:order_success", args=[1]),
            fetch_redirect_response=False,
        )
        order = Order.objects.get(user=self.user)
        item = OrderItem.objects.get(order=order)
        product.refresh_from_db()
        self.assertEqual(order.total, Decimal("300000.00"))
        self.assertEqual(order.payment_method, Order.PaymentMethod.CASH)
        self.assertEqual(item.product_name, product.name)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(product.stock, 3)
        self.assertEqual(self.client.session["cart"], {})

    def test_card_checkout_applies_discount_per_eligible_product(self):
        category = Category.objects.create(name="Kitoblar", slug="kitoblar")
        eligible_product = Product.objects.create(
            category=category,
            name="Eligible book",
            slug="eligible-book",
            price=Decimal("25000.00"),
            stock=3,
        )
        cheap_product = Product.objects.create(
            category=category,
            name="Cheap book",
            slug="cheap-book",
            price=Decimal("15000.00"),
            stock=3,
        )
        self.client.post(reverse("shop:cart_add", args=[eligible_product.id]), {"quantity": 2})
        self.client.post(reverse("shop:cart_add", args=[cheap_product.id]), {"quantity": 1})
        SavedPaymentCard.objects.create(
            user=self.user,
            brand=SavedPaymentCard.Brand.UZCARD,
            last_four='1234',
        )

        response = self.client.post(
            reverse("shop:checkout"),
            {
                "phone": "+998 90 123 45 67",
                "address": "Toshkent, Chilonzor, 12-uy",
                "payment_method": Order.PaymentMethod.CARD,
            },
        )

        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.payment_method, Order.PaymentMethod.CARD)
        self.assertEqual(order.total, Decimal("62500.00"))
        saved_prices = {
            item.product_name: item.price
            for item in order.items.all()
        }
        self.assertEqual(saved_prices["Eligible book"], Decimal("23750.00"))
        self.assertEqual(saved_prices["Cheap book"], Decimal("15000.00"))

    def test_checkout_page_shows_payment_choices_and_totals(self):
        category = Category.objects.create(name="Kitoblar", slug="kitoblar")
        product = Product.objects.create(
            category=category,
            name="Python Darslik",
            slug="python-darslik",
            price=Decimal("25000.00"),
            stock=3,
        )
        self.client.post(reverse("shop:cart_add", args=[product.id]), {"quantity": 1})

        response = self.client.get(reverse("shop:checkout"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="+998"')
        self.assertContains(response, "Naqd pul")
        self.assertContains(response, "Plastik karta")
        self.assertNotContains(response, "Onlayn to‘lov hozircha mavjud emas")
        self.assertNotContains(response, "5% chegirma")
        self.assertContains(response, "Karta qo‘shish")
        self.assertContains(response, "checkout.js?v=1")
        self.assertContains(response, "25 000 so&#x27;m")
        self.assertContains(response, "23 750 so&#x27;m")

    def test_card_checkout_requires_a_saved_card(self):
        category = Category.objects.create(name="Kitoblar", slug="kitoblar")
        product = Product.objects.create(
            category=category,
            name="Python Darslik",
            slug="python-darslik",
            price=Decimal("25000.00"),
            stock=3,
        )
        self.client.post(reverse("shop:cart_add", args=[product.id]), {"quantity": 1})

        response = self.client.post(
            reverse("shop:checkout"),
            {
                "phone": "+998 90 123 45 67",
                "address": "Toshkent, Chilonzor, 12-uy",
                "payment_method": Order.PaymentMethod.CARD,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "avval karta qo‘shing")
        self.assertFalse(Order.objects.exists())

    def test_add_saved_card_stores_only_brand_and_last_four(self):
        response = self.client.post(
            reverse("shop:add_saved_payment_card"),
            {'brand': SavedPaymentCard.Brand.HUMO, 'last_four': '8600'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'success': True,
            'card': {'brand': 'Humo', 'last_four': '8600'},
        })
        card = SavedPaymentCard.objects.get(user=self.user)
        self.assertEqual(card.brand, SavedPaymentCard.Brand.HUMO)
        self.assertEqual(card.last_four, '8600')

    def test_add_saved_card_rejects_invalid_card_metadata(self):
        response = self.client.post(
            reverse("shop:add_saved_payment_card"),
            {'brand': 'visa', 'last_four': '12x4'},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(SavedPaymentCard.objects.exists())

    def test_checkout_rejects_insufficient_stock_without_creating_order(self):
        category = Category.objects.create(name="Kitoblar", slug="kitoblar")
        product = Product.objects.create(
            category=category,
            name="Python Darslik",
            slug="python-darslik",
            price=Decimal("150000.00"),
            stock=2,
        )
        self.client.post(reverse("shop:cart_add", args=[product.id]), {"quantity": 2})
        product.stock = 1
        product.save(update_fields=("stock",))

        response = self.client.post(
            reverse("shop:checkout"),
            {
                "phone": "+998 90 123 45 67",
                "address": "Toshkent, Chilonzor, 12-uy",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Omborda yetarli mahsulot yo‘q")
        self.assertFalse(Order.objects.exists())
        self.assertEqual(self.client.session["cart"][str(product.id)]["quantity"], 2)

    def test_rating_is_limited_to_fifteen_and_user_can_update_it(self):
        category = Category.objects.create(name="Kitoblar", slug="kitoblar")
        product = Product.objects.create(
            category=category,
            name="Python Darslik",
            slug="python-darslik",
            price=Decimal("150000.00"),
            stock=2,
        )
        rating_url = reverse("shop:rate_product", args=[product.id])

        self.assertEqual(self.client.post(rating_url, {"score": 16}).status_code, 302)
        self.assertFalse(ProductRating.objects.exists())
        self.client.post(rating_url, {"score": 12})
        self.client.post(rating_url, {"score": 15})

        self.assertEqual(ProductRating.objects.count(), 1)
        self.assertEqual(ProductRating.objects.get().score, 15)
        response = self.client.get(reverse(
            "shop:product_detail",
            kwargs={"category_slug": category.slug, "product_slug": product.slug},
        ))
        self.assertContains(response, "15")
        self.assertContains(response, "Bahoni yangilash")

    def test_order_success_is_private_to_the_order_owner(self):
        order = Order.objects.create(
            user=self.user,
            phone="+998 90 123 45 67",
            address="Toshkent, Chilonzor, 12-uy",
            total=Decimal("100000.00"),
        )
        another_user = User.objects.create_user(
            username="another-shop-user",
            password="StrongPass123",
        )
        self.client.force_login(another_user)

        response = self.client.get(
            reverse("shop:order_success", args=[order.pk]),
        )

        self.assertEqual(response.status_code, 404)

    def test_order_success_receipt_contains_qr_with_order_details(self):
        order = Order.objects.create(
            user=self.user,
            phone="+998 90 123 45 67",
            address="Toshkent, Chilonzor, 12-uy",
            total=Decimal("100000.00"),
        )
        OrderItem.objects.create(
            order=order,
            product_name="Python Darslik",
            price=Decimal("100000.00"),
            quantity=1,
        )

        with patch("shop.views.qrcode.make", wraps=qrcode.make) as make_qr:
            response = self.client.get(
                reverse("shop:order_success", args=[order.pk])
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'alt="Buyurtma #{order.pk} cheki uchun QR-kod"')
        self.assertTrue(
            base64.b64decode(response.context["qr_code_data"]).startswith(b"<?xml")
        )
        qr_payload = make_qr.call_args.args[0]
        self.assertIn(f"Buyurtma #{order.pk}", qr_payload)
        self.assertIn("Python Darslik x 1", qr_payload)
        self.assertNotIn(order.phone, qr_payload)
        self.assertNotIn(order.address, qr_payload)

    def test_order_can_be_canceled_within_thirty_minutes_and_restores_stock(self):
        category = Category.objects.create(name="Kitoblar", slug="kitoblar")
        product = Product.objects.create(
            category=category,
            name="Python Darslik",
            slug="python-darslik",
            price=Decimal("150000.00"),
            stock=3,
        )
        order = Order.objects.create(
            user=self.user,
            phone="+998 90 123 45 67",
            address="Toshkent, Chilonzor, 12-uy",
            total=Decimal("300000.00"),
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            price=product.price,
            quantity=2,
        )
        product.stock -= 2
        product.save(update_fields=("stock",))

        history = self.client.get(reverse("shop:order_history"))
        self.assertContains(history, "Buyurtmani bekor qilish")

        response = self.client.post(reverse("shop:cancel_order", args=[order.pk]))

        self.assertRedirects(response, reverse("shop:order_history"))
        order.refresh_from_db()
        product.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELED)
        self.assertEqual(product.stock, 3)

    def test_order_cannot_be_canceled_after_thirty_minutes(self):
        order = Order.objects.create(
            user=self.user,
            phone="+998 90 123 45 67",
            address="Toshkent, Chilonzor, 12-uy",
            total=Decimal("100000.00"),
        )
        Order.objects.filter(pk=order.pk).update(
            created_at=timezone.now() - timedelta(minutes=31),
        )

        history = self.client.get(reverse("shop:order_history"))
        response = self.client.post(reverse("shop:cancel_order", args=[order.pk]))

        self.assertNotContains(history, "Buyurtmani bekor qilish")
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertRedirects(response, reverse("shop:order_history"))

    def test_only_order_owner_can_cancel_an_order(self):
        order = Order.objects.create(
            user=self.user,
            phone="+998 90 123 45 67",
            address="Toshkent, Chilonzor, 12-uy",
            total=Decimal("100000.00"),
        )
        another_user = User.objects.create_user(
            username="another-customer",
            password="test-password",
        )
        self.client.force_login(another_user)

        response = self.client.post(reverse("shop:cancel_order", args=[order.pk]))

        self.assertEqual(response.status_code, 404)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)
