(function () {
    'use strict';

    document.addEventListener('input', function (event) {
        if (event.target.id !== 'rating-score') return;
        var output = document.getElementById('rating-output');
        if (output) {
            output.value = event.target.value;
            output.textContent = event.target.value;
        }
    });

    document.addEventListener('click', function (event) {
        var quantityButton = event.target.closest('#qty-minus, #qty-plus');
        if (quantityButton) {
            var input = document.getElementById('qty-input');
            if (!input) return;
            var change = quantityButton.id === 'qty-plus' ? 1 : -1;
            var maxQuantity = parseInt(input.max, 10);
            input.value = Math.min(
                maxQuantity,
                Math.max(1, (parseInt(input.value, 10) || 1) + change)
            );
            return;
        }

        var addButton = event.target.closest('#add-to-cart-detail');
        if (addButton) {
            addToCart(addButton.dataset.productId, Number(
                document.getElementById('qty-input').value
            ));
        }
    });
})();
