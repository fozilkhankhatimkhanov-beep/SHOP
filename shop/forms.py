from django import forms

from .models import Order


class CheckoutForm(forms.Form):
    phone = forms.CharField(
        label='Telefon raqami',
        max_length=32,
        initial='+998',
        widget=forms.TextInput(
            attrs={
                'autocomplete': 'tel',
                'placeholder': '+998 90 123 45 67',
                'inputmode': 'tel',
            },
        ),
    )
    address = forms.CharField(
        label='Yetkazib berish manzili',
        max_length=1000,
        widget=forms.Textarea(
            attrs={
                'autocomplete': 'street-address',
                'placeholder': 'Viloyat, shahar/tuman, ko‘cha va uy',
                'rows': 3,
            },
        ),
    )
    payment_method = forms.ChoiceField(
        label='To‘lov usuli',
        choices=(
            (Order.PaymentMethod.CASH, 'Naqd pul'),
            (Order.PaymentMethod.CARD, 'Plastik karta'),
        ),
        widget=forms.RadioSelect(),
        required=False,
        initial=Order.PaymentMethod.CASH,
    )

    def clean_phone(self):
        phone = ' '.join(self.cleaned_data['phone'].split())
        if sum(character.isdigit() for character in phone) < 7:
            raise forms.ValidationError('Telefon raqamini to‘g‘ri kiriting.')
        return phone

    def clean_address(self):
        address = self.cleaned_data['address'].strip()
        if len(address) < 8:
            raise forms.ValidationError('Yetkazib berish manzilini to‘liq kiriting.')
        return address

    def clean_payment_method(self):
        return self.cleaned_data['payment_method'] or Order.PaymentMethod.CASH
