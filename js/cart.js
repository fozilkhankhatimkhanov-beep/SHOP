function addToCart(productId, quantity) {
    quantity = quantity || 1;
    fetch('/cart/add/' + productId + '/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'quantity=' + quantity,
    })
    .then(function (res) { return res.json(); })
    .then(function (data) {
        if (data.success) {
            updateCartCount(data.cart_count);
            showMessage('Mahsulot savatga qo\'shildi!');
        }
    })
    .catch(function () {
        showMessage('Xatolik yuz berdi.');
    });
}

function removeFromCart(productId) {
    fetch('/cart/remove/' + productId + '/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    })
    .then(function (res) { return res.json(); })
    .then(function (data) {
        if (data.success) {
            updateCartCount(data.cart_count);
            window.location.href = '/cart/';
        }
    });
}

function updateQuantity(productId, quantity) {
    quantity = Math.max(1, quantity);
    fetch('/cart/add/' + productId + '/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'quantity=' + quantity,
    })
    .then(function (res) { return res.json(); })
    .then(function (data) {
        if (data.success) {
            updateCartCount(data.cart_count);
            location.reload();
        }
    });
}

function clearCart() {
    fetch('/cart/clear/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
        },
    })
    .then(function (res) { return res.json(); })
    .then(function (data) {
        if (data.success) {
            updateCartCount(0);
            window.location.href = '/cart/';
        }
    });
}

function updateCartCount(count) {
    var el = document.querySelector('.cart-count');
    if (el) el.textContent = count;
}

function showMessage(msg) {
    alert(msg);
}

function getCookie(name) {
    var val = document.cookie.match('(^|;)\s*' + name + '\s*=\s*([^;]+)');
    return val ? val.pop() : '';
}

document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.add-to-cart-btn:not([disabled])').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var productId = this.dataset.productId;
            addToCart(productId, 1);
        });
    });
});
