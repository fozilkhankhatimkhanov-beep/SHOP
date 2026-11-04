"""Haqiqiy mahsulot fotosuratlarini Wikimedia Commons'dan olib kelish.

Har bir mahsulot slug'i uchun mos qidiruv so'rovlari berilgan (birinchi
ishlaydigan so'rov ishlatiladi). Faqat JPEG fotosuratlar olinadi — sxema,
diagramma va skanerlangan sahifalar chetlab o'tiladi. Rasm 600x500 JPEG
ko'rinishida `media/products/<slug>.jpg` ga saqlanadi, manba ma'lumoti esa
`media/products/CREDITS.txt` fayliga yoziladi (litsenziya talabi).
"""
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageOps

USER_AGENT = "OnlaynBozorDemo/1.0 (educational Django project)"

# Mahsulot slug'i -> mos qidiruvlar (muqobil variantlar bilan)
PHOTO_QUERIES = {
    # Elektronika
    "smartfon-x200": ("intitle:smartphone white", "intitle:Samsung Galaxy phone", "intitle:smartphone"),
    "laptop-pro-15": ("intitle:laptop", "intitle:laptop computer", "laptop computer photo"),
    "ploskincha-64gb": ("intitle:SD card", "intitle:microSD card", "intitle:memory card"),
    "noutbuk-stoli": ("intitle:laptop desk", "intitle:laptop table", "intitle:desk laptop"),
    "simsiz-quloqchin": ("intitle:earbuds", "intitle:headphones", "intitle:wireless earbuds"),
    "simsiz-sichqoncha": ("intitle:computer mouse", "intitle:wireless mouse", "intitle:mouse device"),
    "aqlli-soat": ("intitle:smartwatch", "intitle:smart watch", "intitle:sport watch"),
    # Idish-tovoqlar
    "qozon": ("intitle:cooking pot", "intitle:stockpot", "intitle:cauldron cooking"),
    "qovurish-tovasi": ("intitle:frying pan", "intitle:skillet pan", "intitle:cast iron pan"),
    "likopchalar-toplami": ("intitle:dinnerware", "intitle:plate set", "intitle:porcelain plates"),
    "choynak": ("intitle:teapot", "intitle:tea pot", "intitle:kettle"),
    # Kitoblar
    "python-darslik": ("intitle:programming code screen", "intitle:Python code", "intitle:computer code"),
    "ingliz-tili": ("intitle:english textbook", "intitle:english grammar book", "intitle:english book"),
    "matematika-5-sinf": ("intitle:mathematics textbook", "intitle:math book", "intitle:mathematics book"),
    "adabiyot-antologiya": ("intitle:books stack", "intitle:stack of books", "intitle:poetry book"),
    "bolalar-ertaklari": ("intitle:children's books", "intitle:picture book", "intitle:childrens books"),
    "uzbek-ingliz-lugat": ("intitle:Uzbek dictionary", "intitle:bilingual dictionary", "intitle:english dictionary"),
    # Kiyim-kechak
    "jasur-yaktak": ("intitle:raincoat", "intitle:rain jacket", "intitle:waterproof jacket"),
    "kettes-m1": ("intitle:sneakers", "intitle:trainers shoes", "intitle:casual shoes"),
    "sportchilik-jinsi": ("intitle:sweatpants", "intitle:jogging trousers", "intitle:tracksuit"),
    "krossok": ("intitle:running shoes", "intitle:running shoe", "intitle:athletic shoes"),
    "paxtali-futbolka": ("intitle:T-shirt", "intitle:t shirt cotton", "intitle:white t-shirt"),
    "klassik-jinsi-shim": ("intitle:jeans", "intitle:denim trousers", "intitle:blue jeans"),
    "kundalik-koylak": ("intitle:dress shirt", "intitle:shirt clothing", "intitle:men shirt"),
    # O'yinchoqlar
    "lego-city-set": ("intitle:lego bricks", "intitle:lego", "intitle:lego toy"),
    "m-diy-robot": ("intitle:toy robot", "intitle:robot toy", "intitle:humanoid robot toy"),
    "puzzles-500": ("intitle:jigsaw puzzle", "intitle:puzzle pieces", "intitle:puzzle"),
    "rangli-kubiklar": ("intitle:toy blocks", "intitle:wooden toy blocks", "intitle:building blocks toy"),
    "bolalar-stol-oyini": ("intitle:board game playing", "intitle:tabletop game", "intitle:board game box"),
    # Oshxona
    "elektr-choynak": ("intitle:electric kettle", "intitle:water kettle", "intitle:kettle appliance"),
    "blender": ("intitle:kitchen blender", "intitle:blender appliance", "intitle:stand blender"),
    "toster": ("intitle:toaster appliance", "intitle:bread toaster", "intitle:toasters"),
    "kesish-taxtasi": ("intitle:chopping board", "intitle:wooden cutting board", "intitle:cutting board kitchen"),
    # Sport
    "yoga-gilamchasi": ("intitle:yoga mat", "intitle:exercise mat", "intitle:yoga mats"),
    "sakrash-arqoni": ("intitle:skipping rope", "intitle:jump rope", "intitle:rope skipping"),
    "gantel-jufti": ("intitle:dumbbells", "intitle:dumbbell weights", "intitle:weight dumbbell"),
    "futbol-topi": ("intitle:soccer ball", "intitle:football ball", "intitle:soccer ball close"),
    # Uy-ro'zg'or
    "stol-chirogi": ("intitle:desk lamp", "intitle:table lamp", "intitle:reading lamp"),
    "kiyim-ilgich": ("intitle:clothes hanger", "intitle:clothes hangers", "intitle:coat hanger"),
    "yumshoq-adyol": ("intitle:wool blanket", "intitle:folded blanket", "intitle:bed blanket"),
    "saqlash-qutisi": ("intitle:storage box", "intitle:plastic storage container", "intitle:storage bins"),
}

# Fotosurat bo'lmagan (sxema, logotip, skaner) fayllarni chetlab o'tish
_SKIP_WORDS = (
    "logo", "icon", "diagram", "chart", "symbol", "clipart", "screenshot",
    "drawing", "scheme", "sign", "banner", "coat of arms", "flag", "map",
    "schematic", "patent", "illustration", "plot", "graph", "sketch",
    "cartoon", "poster", "newspaper", "page", "text", "book cover", "bw",
)

IMAGE_SIZE = (600, 500)


def _fetch(url, timeout=30, retries=4):
    """Commons ba'zan javobni cheklaydi (429) — kutib qayta urinamiz."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            return urllib.request.urlopen(request, timeout=timeout).read()
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 503) or attempt == retries - 1:
                raise
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("unreachable")


def _commons_search(query, limit=12):
    """Commons'dan mos keladigan rasm havolalarini qidiruv tartibida qaytaradi."""
    params = urllib.parse.urlencode({
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrnamespace": 6,
        "gsrlimit": limit,
        "gsrsearch": "filetype:bitmap " + query,
        "prop": "imageinfo",
        "iiprop": "url|mime|size",
        "iiurlwidth": 1200,
    })
    data = json.loads(_fetch("https://commons.wikimedia.org/w/api.php?" + params))
    pages = data.get("query", {}).get("pages", {})

    results = []
    for page in pages.values():
        title = page.get("title", "")
        lowered = title.lower()
        if any(word in lowered for word in _SKIP_WORDS):
            continue
        info = (page.get("imageinfo") or [{}])[0]
        # Faqat haqiqiy fotosuratlar: JPEG
        if info.get("mime") != "image/jpeg":
            continue
        width = info.get("width") or 0
        height = info.get("height") or 0
        if width < 500 or height < 400:
            continue
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        results.append({
            "title": title,
            "url": url,
            "page": info.get("descriptionurl", ""),
        })
    return results


def _normalize(raw):
    """Rasmni 600x500 o'lchamga keltiradi (markazdan kesib)."""
    image = Image.open(io.BytesIO(raw))
    image = ImageOps.exif_transpose(image).convert("RGB")
    return ImageOps.fit(image, IMAGE_SIZE, method=Image.LANCZOS, centering=(0.5, 0.5))


def _write_credit(slug, item):
    credits = Path(settings.MEDIA_ROOT) / "products" / "CREDITS.txt"
    credits.parent.mkdir(parents=True, exist_ok=True)
    with credits.open("a", encoding="utf-8") as fh:
        fh.write(f"{slug}.jpg\t{item['title']}\t{item['page']}\n")


def ensure_product_photo(slug, overwrite=False):
    """Mahsulot uchun haqiqiy fotosurat yuklab, `products/<slug>.jpg` yo'lini qaytaradi."""
    relative = f"products/{slug}.jpg"
    target = Path(settings.MEDIA_ROOT) / relative
    if target.exists() and not overwrite:
        return relative

    queries = PHOTO_QUERIES.get(slug)
    if not queries:
        return None
    if isinstance(queries, str):
        queries = (queries,)

    for query in queries:
        try:
            candidates = _commons_search(query)
        except Exception:
            continue
        for item in candidates:
            try:
                image = _normalize(_fetch(item["url"]))
            except Exception:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            image.save(target, "JPEG", quality=88, optimize=True)
            _write_credit(slug, item)
            return relative
        time.sleep(1.0)
    return None
