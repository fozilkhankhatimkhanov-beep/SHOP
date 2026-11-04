from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path

from PIL import Image, ImageDraw

from shop.models import Category, Product
from shop.photo_sources import PHOTO_QUERIES, ensure_product_photo


class Command(BaseCommand):
    help = "Demo kategoriya va mahsulotlarni haqiqiy fotosuratlar bilan to'ldiradi."

    CATEGORIES = [
        ("Elektronika", "elektronika"),
        ("Kiyim-kechak", "kiyim-kechak"),
        ("O'yinchoqlar", "oyinchoqlar"),
        ("Kitoblar", "kitoblar"),
        ("Sport", "sport"),
        ("Idish-tovoqlar", "idish-tovoq"),
        ("Uy-ro'zg'or", "uy-rozgor"),
        ("Oshxona", "oshxona"),
    ]

    PRODUCTS = [
        ("elektronika", [
            ("Noutbuk Pro 15", "laptop-pro-15", 12000000, 10, "15 dyuymli ekran, 16 GB operativ xotira va tez SSD disk. Ish va o'qish uchun qulay."),
            ("Smartfon X200", "smartfon-x200", 5000000, 20, "Yorqin ekran, sifatli kamera va uzoq ishlaydigan batareya bilan kundalik foydalanish uchun."),
            ("Xotira kartasi 64 GB", "ploskincha-64gb", 850000, 50, "Telefon, kamera va planshet uchun mos 64 GB microSD xotira kartasi."),
            ("Noutbuk uchun taglik", "noutbuk-stoli", 1500000, 15, "Noutbukni qulay balandlikda ushlash uchun sozlanadigan taglik."),
            ("Simsiz quloqchin", "simsiz-quloqchin", 390000, 25, "Musiqa va qo'ng'iroqlar uchun ixcham simsiz quloqchin."),
            ("Simsiz sichqoncha", "simsiz-sichqoncha", 180000, 35, "Kompyuter va noutbuk bilan ishlaydigan qulay simsiz sichqoncha."),
            ("Aqlli soat", "aqlli-soat", 750000, 18, "Vaqt, faollik va bildirishnomalarni ko'rsatadigan aqlli soat."),
        ]),
        ("kiyim-kechak", [
            ("Kets krossovkasi M1", "kettes-m1", 600000, 20, "Yengil krossovka, kundalik kiyish va uzoq yurish uchun qulay."),
            ("Yomg'irpo'sh yaktak", "jasur-yaktak", 850000, 12, "Yomg'irli kunlarda kiyish uchun yengil, kapyushonli yaktak."),
            ("Sport shim", "sportchilik-jinsi", 450000, 40, "Elastik matoli yengil shim, mashg'ulot va kundalik kiyim uchun."),
            ("Yugurish krossovkasi", "krossok", 180000, 60, "Yumshoq tagcharmli krossovka, yugurish va sayr uchun."),
            ("Paxtali futbolka", "paxtali-futbolka", 160000, 30, "Yumshoq paxtali matodan tikilgan kundalik futbolka."),
            ("Klassik jinsi shim", "klassik-jinsi-shim", 320000, 24, "Kundalik kiyimlar bilan mos keladigan klassik jinsi shim."),
            ("Kundalik ko'ylak", "kundalik-koylak", 280000, 18, "Kundalik foydalanish uchun yengil va qulay ko'ylak."),
        ]),
        ("oyinchoqlar", [
            ("LEGO City to'plami", "lego-city-set", 1200000, 10, "Shahar mavzusidagi konstruktor to'plami, 6 yoshdan katta bolalar uchun."),
            ("DIY robot to'plami", "m-diy-robot", 900000, 14, "Yig'ma robot to'plami, ijodkorlik va muhandislik fikrlashini rivojlantirish uchun."),
            ("Pazl, 500 bo'lak", "puzzles-500", 220000, 30, "Diqqat va mantiqiy fikrlashni rivojlantiradigan 500 bo'lakli pazl."),
            ("Rangli kubiklar", "rangli-kubiklar", 190000, 25, "Turli shakllar yasash uchun rangli qurilish kubiklari."),
            ("Bolalar stol o'yini", "bolalar-stol-oyini", 250000, 16, "Oila davrasida birgalikda o'ynash uchun qiziqarli stol o'yini."),
        ]),
        ("kitoblar", [
            ("Ingliz tili darsligi", "ingliz-tili", 200000, 10, "Boshlang'ich daraja uchun grammatika va so'z mashqlari bilan ingliz tili darsligi."),
            ("Python darsligi", "python-darslik", 150000, 10, "Python dasturlash tilini noldan o'rganish uchun amaliy qo'llanma."),
            ("Matematika, 5-sinf", "matematika-5-sinf", 120000, 20, "5-sinf o'quvchilari uchun misol va masalalarga boy matematika darsligi."),
            ("Adabiyot antologiyasi", "adabiyot-antologiya", 180000, 8, "Maktab o'quvchilari uchun adabiy asarlar to'plami."),
            ("Bolalar uchun ertaklar", "bolalar-ertaklari", 95000, 15, "Bolalar bilan mutolaa qilish uchun xalq ertaklari to'plami."),
            ("O'zbekcha-inglizcha lug'at", "uzbek-ingliz-lugat", 110000, 12, "O'zbek va ingliz tillaridagi so'zlarni topish uchun ixcham lug'at."),
        ]),
        ("sport", [
            ("Yoga gilamchasi", "yoga-gilamchasi", 220000, 20, "Uyda mashq va cho'zilish mashqlari uchun sirpanmaydigan gilamcha."),
            ("Sakrash arqoni", "sakrash-arqoni", 90000, 30, "Kardio mashqlari uchun uzunligi sozlanadigan yengil arqon."),
            ("Gantel jufti", "gantel-jufti", 350000, 12, "Uy sharoitidagi kuch mashqlari uchun qulay gantel jufti."),
            ("Futbol to'pi", "futbol-topi", 280000, 18, "Ochiq maydon va mashg'ulotlar uchun futbol to'pi."),
        ]),
        ("idish-tovoq", [
            ("Qozon", "qozon", 480000, 15, "Oilaviy taomlar tayyorlash uchun mustahkam qozon."),
            ("Qovurish tovasi", "qovurish-tovasi", 320000, 14, "Kundalik ovqat tayyorlash uchun qulay qovurish tovasi."),
            ("Likopchalar to'plami", "likopchalar-toplami", 260000, 20, "Dasturxon uchun kundalik foydalanishga mo'ljallangan likopchalar to'plami."),
            ("Choynak", "choynak", 180000, 22, "Choy damlash uchun qulay va yuvish oson choynak."),
        ]),
        ("uy-rozgor", [
            ("Stol chirog'i", "stol-chirogi", 210000, 16, "O'qish va ishlash uchun ixcham stol chirog'i."),
            ("Kiyim ilgich", "kiyim-ilgich", 120000, 24, "Kiyimlarni tartibli saqlash uchun mustahkam ilgichlar to'plami."),
            ("Yumshoq adyol", "yumshoq-adyol", 390000, 10, "Uyda foydalanish uchun issiq va yumshoq adyol."),
            ("Saqlash qutisi", "saqlash-qutisi", 150000, 20, "Uy buyumlarini tartibli joylash uchun qopqoqli quti."),
        ]),
        ("oshxona", [
            ("Elektr choynak", "elektr-choynak", 290000, 18, "Suvni tez qaynatish uchun avtomatik o'chadigan elektr choynak."),
            ("Blender", "blender", 520000, 11, "Ichimlik va yengil taomlar tayyorlash uchun oshxona blenderi."),
            ("Toster", "toster", 410000, 9, "Non bo'laklarini qizartirib tayyorlaydigan ixcham toster."),
            ("Kesish taxtasi", "kesish-taxtasi", 85000, 25, "Oshxonada mahsulot to'g'rash uchun qulay kesish taxtasi."),
        ]),
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove existing categories/products before seeding.",
        )
        parser.add_argument(
            "--refresh-images",
            action="store_true",
            help="Mavjud mahsulotlar uchun fotosuratlarni qaytadan yuklash.",
        )
        parser.add_argument(
            "--skip-photos",
            action="store_true",
            help="Fotosurat yuklamasdan, mahalliy mahsulot rasmlaridan foydalanish.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            Product.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared existing data."))

        if options["refresh_images"]:
            for product in Product.objects.exclude(slug=""):
                if product.slug in PHOTO_QUERIES:
                    relative = ensure_product_photo(product.slug, overwrite=True)
                    if relative:
                        product.image = relative
                        product.save(update_fields=["image"])
                        self.stdout.write(f"Photo updated: {product.slug}")
            self.stdout.write(self.style.SUCCESS("Rasmlar yangilandi."))
            return

        categories = {}
        for cname, cslug in self.CATEGORIES:
            category, created = Category.objects.update_or_create(
                slug=cslug,
                defaults={"name": cname},
            )
            categories[cslug] = category
            self.stdout.write(f"{'Created' if created else 'Updated'} category: {cname}")

        for category_slug, prods in self.PRODUCTS:
            category = categories[category_slug]
            for pname, pslug, price, stock, desc in prods:
                product, created = Product.objects.update_or_create(
                    slug=pslug,
                    defaults={
                        "category": category,
                        "name": pname,
                        "price": price,
                        "stock": stock,
                        "description": desc,
                        "is_available": stock > 0,
                    },
                )

                relative = None
                if not options["skip_photos"]:
                    relative = ensure_product_photo(pslug)
                if relative and product.image != relative:
                    product.image = relative
                    product.save(update_fields=["image"])
                    self.stdout.write(f"Assigned photo: {relative}")
                elif not product.image:
                    self.create_placeholder_image(product)
                self.stdout.write(f"{'Created' if created else 'Updated'} product: {pname}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete. Categories: {Category.objects.count()}, "
                f"Products: {Product.objects.count()}"
            )
        )

    def create_placeholder_image(self, product):
        image_dir = Path(settings.MEDIA_ROOT) / "products"
        image_dir.mkdir(parents=True, exist_ok=True)
        path = image_dir / f"{product.slug}.png"
        if path.exists():
            return

        colors = {
            "elektronika": (68, 96, 180),
            "kiyim-kechak": (150, 90, 160),
            "oyinchoqlar": (220, 170, 70),
            "kitoblar": (150, 105, 65),
            "sport": (200, 90, 90),
            "idish-tovoq": (70, 145, 145),
            "uy-rozgor": (100, 135, 105),
            "oshxona": (190, 130, 75),
        }
        image = Image.new("RGB", (600, 500), colors.get(product.category.slug, (110, 125, 145)))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((70, 90, 530, 410), radius=36, fill=(255, 255, 255))
        draw.text((100, 220), product.name[:34], fill=(45, 52, 54))
        image.save(path)
