# Shop1

Onlayn do'kon Django loyihasi.

## Tuzilishi

- `manage.py` — Django buyruqlarini ishga tushirish.
- `myshop/` — loyiha sozlamalari, URL va ASGI/WSGI konfiguratsiyasi.
- `shop/` — mahsulotlar, savat, buyurtmalar, admin va ularning testlari.
- `shop_auth/` — ro'yxatdan o'tish, kirish va parol boshqaruvi.
- `templates/` va `static/` — umumiy HTML shablonlar va statik fayllar.
- `media/` — yuklangan/namuna rasmlar; `db.sqlite3` — mahalliy ma'lumotlar bazasi.

## Buyruqlar

```text
python manage.py runserver
python manage.py test
python manage.py seed_data
```
