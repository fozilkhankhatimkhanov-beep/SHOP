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
            markProductInCart(productId, data.product_quantity);
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
            return fillCartFromServer();
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
    var cartLink = document.querySelector('.cart-icon');
    if (!cartLink) return;

    var el = cartLink.querySelector('.cart-count');
    if (count > 0) {
        if (!el) {
            el = document.createElement('span');
            el.className = 'cart-count';
            cartLink.appendChild(el);
        }
        el.textContent = count;
    } else if (el) {
        el.remove();
    }
}

function markProductInCart(productId, quantity) {
    document.querySelectorAll('[data-product-id="' + productId + '"]').forEach(function (button) {
        button.classList.add('in-cart');
        button.dataset.cartQuantity = quantity;
        button.textContent = 'Savatda (' + quantity + 'x) ✓';
    });
}

function fillCartFromServer() {
    return fetch('/cart/')
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
            }
        })
        .catch(showCartError);
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

function initializeCartPage() {
    fillPlaceholderImage();
}

document.addEventListener('DOMContentLoaded', initializeCartPage);
document.addEventListener('site:page-loaded', initializeCartPage);

document.addEventListener('click', function (event) {
    var quantityButton = event.target.closest('.cart-qty-btn');
    if (quantityButton) {
        var row = quantityButton.closest('.cart-item-row');
        var input = row.querySelector('.cart-qty-input');
        var quantity = parseInt(input.value, 10);
        var maxQuantity = parseInt(input.max, 10);
        var change = quantityButton.dataset.action === 'increase' ? 1 : -1;
        var nextQuantity = Math.min(maxQuantity, Math.max(1, quantity + change));

        if (nextQuantity !== quantity) {
            row.querySelectorAll('.cart-qty-btn').forEach(function (control) {
                control.disabled = true;
            });
            updateQuantity(input.dataset.productId, nextQuantity).then(function () {
                if (row.isConnected) {
                    row.querySelectorAll('.cart-qty-btn').forEach(function (control) {
                        control.disabled = false;
                    });
                }
            });
        }
        return;
    }

    var removeButton = event.target.closest('.remove-item-btn');
    if (removeButton) {
        removeFromCart(removeButton.dataset.productId);
        return;
    }

    if (event.target.closest('#clear-cart-btn')) {
        if (confirm('Savatni tozalamoqchimisiz?')) clearCart();
        return;
    }

    var addButton = event.target.closest('.add-to-cart-btn:not([disabled])');
    if (addButton) {
        event.preventDefault();
        addToCart(addButton.dataset.productId, 1);
    }
});
