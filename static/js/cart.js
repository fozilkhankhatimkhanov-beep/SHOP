var CART_URLS = CART_URLS || {};

function addToCart(productId, quantity) {
    quantity = quantity || 1;
    return fetch(CART_URLS.add.replace(':id', productId), {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'quantity=' + quantity,
    })
    .then(handleCartResponse)
    .then(function (data) {
        if (data.success) {
            updateCartCount(data.cart_count);
            showMessage('Mahsulot savatga qo\'shildi!');
        }
        return data;
    })
    .catch(showCartError);
}

function removeFromCart(productId) {
    return fetch(CART_URLS.remove.replace(':id', productId), {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    })
    .then(handleCartResponse)
    .then(function (data) {
        if (data.success) {
            updateCartCount(data.cart_count);
            fillCartFromServer();
        }
        return data;
    })
    .catch(showCartError);
}

function updateQuantity(productId, quantity) {
    quantity = Math.max(1, quantity);
    return fetch(CART_URLS.update.replace(':id', productId), {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'quantity=' + quantity,
    })
    .then(handleCartResponse)
    .then(function (data) {
        if (data.success) {
            updateCartCount(data.cart_count);
            fillCartFromServer();
        }
        return data;
    })
    .catch(showCartError);
}

function clearCart() {
    return fetch(CART_URLS.clear, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
        },
    })
    .then(handleCartResponse)
    .then(function (data) {
        if (data.success) {
            updateCartCount(0);
            fillCartFromServer();
        }
        return data;
    })
    .catch(showCartError);
}

function handleCartResponse(response) {
    return response.json().then(function (data) {
        if (!response.ok) {
            throw new Error(data.error || 'So‘rovni bajarib bo‘lmadi.');
        }
        return data;
    });
}

function showCartError(error) {
    showMessage(error.message || 'Server bilan bog‘lanishda xatolik yuz berdi.');
}

function updateCartCount(count) {
    var el = document.querySelector('.cart-count');
    if (el) el.textContent = count;
}

function fillCartFromServer() {
    fetch('/cart/')
        .then(function (res) { return res.text(); })
        .then(function (html) {
            var parser = new DOMParser();
            var doc = parser.parseFromString(html, 'text/html');

            var serverCartCount = doc.querySelector('.cart-count');
            if (serverCartCount) updateCartCount(parseInt(serverCartCount.textContent, 10) || 0);

            var serverCartState = doc.querySelector('.cart-container, .empty-cart');
            var localCartState = document.querySelector('.cart-container, .empty-cart');
            if (serverCartState && localCartState) {
                localCartState.replaceWith(serverCartState.cloneNode(true));
                initializeCartSummary();
            }
        })
        .catch(showCartError);
}

function initializeCartSummary() {
    document.querySelectorAll('.cart-qty-input').forEach(function (input) {
        input.addEventListener('change', function () {
            var quantity = parseInt(this.value, 10);
            if (!Number.isInteger(quantity) || quantity < 1) {
                quantity = 1;
                this.value = quantity;
            }
            updateQuantity(this.dataset.productId, quantity);
        });
    });

    document.querySelectorAll('.remove-item-btn').forEach(function (button) {
        button.addEventListener('click', function () {
            if (confirm('Savatdan o‘chirmoqchimisiz?')) {
                removeFromCart(this.dataset.productId);
            }
        });
    });

    var clearButton = document.getElementById('clear-cart-btn');
    if (clearButton) {
        clearButton.addEventListener('click', function () {
            if (confirm('Savatni tozalamoqchimisiz?')) {
                clearCart();
            }
        });
    }
}

function showMessage(msg) {
    var existing = document.querySelector('.toast-message');
    if (existing) existing.remove();

    var toast = document.createElement('div');
    toast.className = 'toast-message';
    toast.textContent = msg;
    document.body.appendChild(toast);

    setTimeout(function () {
        if (toast.parentNode) toast.remove();
    }, 3000);
}

function getCookie(name) {
    var val = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    if (val) return val.pop();
    var token = document.querySelector('meta[name="csrf-token"]');
    return name === 'csrftoken' && token ? token.content : '';
}

function resolveProductImageByName(name) {
    if (!name) return null;
    var cleaned = name
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, '')
        .trim();
    var map = {
        'adabiyot antologiya': 'adabiyot-antologiya.png',
        'matematika 5-sinf': 'matematika-5-sinf.png',
        'puzzles 500 ta': 'puzzles-500.png',
        'm diy robot': 'm-diy-robot.png',
        'krossok': 'krossok.png',
        'sportchilik jinsi': 'sportchilik-jinsi.png',
        'noutbuk stoli': 'noutbuk-stoli.png',
        'ploskincha 64 gb': 'ploskincha-64gb.png',
        'ingliz tili': 'ingliz-tili.png',
        'python darslik': 'python-darslik.png',
        'lego city set': 'lego-city-set.png',
        'kettes m1': 'kettes-m1.png',
        'jasur yaktak': 'jasur-yaktak.png',
        'laptop pro 15': 'laptop-pro-15.png',
        'smartfon x200': 'smartfon-x200.png'
    };
    var file = map[cleaned];
    if (!file) {
        var normalized = cleaned.replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
        var candidates = Object.keys(map).filter(function (key) {
            var norm = key.toLowerCase().replace(/\s+/g, '-');
            return norm.indexOf(normalized) !== -1 || normalized.indexOf(norm) !== -1;
        });
        var match = candidates.length ? map[candidates[0]] : null;
        file = match;
    }
    return file;
}

function fillPlaceholderImage() {
    document.querySelectorAll('.product-image-placeholder[data-name]').forEach(function (placeholder) {
        var name = (placeholder.getAttribute('data-name') || '').trim();
        var file = placeholder.getAttribute('data-image') || resolveProductImageByName(name);
        if (!file) return;
        var img = new Image();
        img.src = '/media/products/' + file;
        img.onerror = function () {
            placeholder.style.background = 'linear-gradient(135deg, #dfe6e9, #b2bec3)';
            placeholder.textContent = '📦';
        };
        img.onload = function () {
            img.className = placeholder.classList.contains('large') ? 'product-main-image' : 'product-image';
            img.alt = name;
            placeholder.replaceWith(img);
        };
    });
}

document.addEventListener('DOMContentLoaded', function () {
    fillPlaceholderImage();
    initializeCartSummary();
    document.querySelectorAll('.add-to-cart-btn:not([disabled])').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            var productId = this.dataset.productId;
            addToCart(productId, 1);
            return false;
        });
    });
});
