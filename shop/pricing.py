from decimal import Decimal, ROUND_HALF_UP


CARD_DISCOUNT_THRESHOLD = Decimal('20000.00')
CARD_DISCOUNT_RATE = Decimal('0.05')


def discounted_card_price(price):
    amount = Decimal(str(price))
    if amount < CARD_DISCOUNT_THRESHOLD:
        return amount
    return (amount * (Decimal('1.00') - CARD_DISCOUNT_RATE)).quantize(
        Decimal('0.01'),
        rounding=ROUND_HALF_UP,
    )
