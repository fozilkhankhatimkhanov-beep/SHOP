from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def uzs(value):
    """Narxni o'zbekcha ko'rinishda chiqaradi: 180000.00 -> "180 000 so'm"."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return value
    formatted = f"{amount:,.0f}".replace(",", " ")
    return f"{formatted} so'm"
