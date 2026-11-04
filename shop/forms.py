from django import forms


class CheckoutForm(forms.Form):
    phone = forms.CharField(
        label='Telefon raqami',
        max_length=32,
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
