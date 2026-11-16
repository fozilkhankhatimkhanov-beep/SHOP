(function () {
    'use strict';

    var paymentOptions = document.querySelectorAll('input[name="payment_method"]');
    var cardManagement = document.getElementById('card-management');
    if (!paymentOptions.length || !cardManagement) return;

    var cardEntry = document.getElementById('card-entry');
    var cardToggle = document.getElementById('add-card-toggle');
    var cardNumber = document.getElementById('card-number');
    var cardTypeStatus = document.getElementById('card-type-status');
    var cardAddStatus = document.getElementById('card-add-status');
    var saveCardButton = document.getElementById('save-card-button');
    var savedCardList = document.getElementById('saved-card-list');
    var checkoutForm = document.querySelector('.checkout-form');
    var cardBrand = '';
    var cardDigits = '';

    function setAddStatus(message, status) {
        cardAddStatus.textContent = message;
        cardAddStatus.dataset.status = status || '';
    }

    function updateCardManagement() {
        var cardSelected = Array.prototype.some.call(paymentOptions, function (option) {
            return option.checked && option.value === 'card';
        });
        cardManagement.hidden = !cardSelected;
        if (!cardSelected) {
            cardNumber.value = '';
            cardDigits = '';
            cardBrand = '';
            cardTypeStatus.textContent = '';
            saveCardButton.disabled = true;
            cardEntry.hidden = true;
            setAddStatus('', '');
        }
    }

    function getCardBrand(digits) {
        if (digits.indexOf('5614') === 0 || digits.indexOf('8600') === 0) {
            return {value: 'uzcard', label: 'Uzcard'};
        }
        if (digits.indexOf('9860') === 0) {
            return {value: 'humo', label: 'Humo'};
        }
        return null;
    }

    paymentOptions.forEach(function (option) {
        option.addEventListener('change', updateCardManagement);
    });
    updateCardManagement();

    cardToggle.addEventListener('click', function () {
        cardEntry.hidden = !cardEntry.hidden;
        if (!cardEntry.hidden) cardNumber.focus();
    });

    cardNumber.addEventListener('input', function () {
        cardDigits = cardNumber.value.replace(/\D/g, '').slice(0, 16);
        cardNumber.value = cardDigits.replace(/(\d{4})(?=\d)/g, '$1 ');
        var detected = getCardBrand(cardDigits);
        cardBrand = detected ? detected.value : '';
        saveCardButton.disabled = !detected || cardDigits.length !== 16;

        if (!cardDigits) {
            cardTypeStatus.textContent = '';
        } else if (!detected && cardDigits.length >= 4) {
            cardTypeStatus.textContent = 'Faqat Uzcard (5614/8600) yoki Humo (9860) kartasi.';
        } else if (detected) {
            cardTypeStatus.textContent = detected.label + ' kartasi';
            if (cardDigits.length === 16) {
                cardTypeStatus.textContent += ' •••• ' + cardDigits.slice(-4);
            }
        } else {
            cardTypeStatus.textContent = 'Karta raqamini kiriting.';
        }
        setAddStatus('', '');
    });

    saveCardButton.addEventListener('click', function () {
        if (!cardBrand || cardDigits.length !== 16) return;

        saveCardButton.disabled = true;
        setAddStatus('', '');
        var csrfInput = checkoutForm.querySelector('[name="csrfmiddlewaretoken"]');
        var body = new URLSearchParams({
            brand: cardBrand,
            last_four: cardDigits.slice(-4),
        });

        fetch(cardManagement.dataset.addCardUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'X-CSRFToken': csrfInput.value,
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: body.toString(),
        })
            .then(function (response) {
                return response.json().then(function (data) {
                    if (!response.ok || !data.success) {
                        throw new Error(data.error || 'Kartani qo‘shib bo‘lmadi.');
                    }
                    return data;
                });
            })
            .then(function (data) {
                var row = document.createElement('div');
                var label = document.createElement('span');
                var lastFour = document.createElement('strong');
                row.className = 'saved-card';
                label.textContent = data.card.brand;
                lastFour.textContent = '•••• ' + data.card.last_four;
                row.appendChild(label);
                row.appendChild(lastFour);
                savedCardList.appendChild(row);

                cardEntry.hidden = true;
                cardToggle.textContent = 'Boshqa karta qo‘shish';
                setAddStatus('Karta qo‘shildi. To‘liq karta raqami saqlanmadi.', 'success');
                cardDigits = '';
                cardBrand = '';
                cardNumber.value = '';
                cardTypeStatus.textContent = '';
            })
            .catch(function (error) {
                setAddStatus(error.message || 'Kartani qo‘shishda xatolik yuz berdi.', 'error');
            })
            .then(function () {
                saveCardButton.disabled = !cardBrand || cardDigits.length !== 16;
            });
    });
})();
