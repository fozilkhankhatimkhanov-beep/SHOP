import tempfile
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from decimal import Decimal

from shop.models import Category, Order, OrderItem, Product, ProductRating


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
        self.assertEqual(item.product_name, product.name)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(product.stock, 3)
        self.assertEqual(self.client.session["cart"], {})

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
