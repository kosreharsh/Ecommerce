from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget

PAYMENT_CHOICES = (
    ('S', 'Stripe'),
    ('P', 'PayTm'),
)
class CheckOutForm(forms.Form):
    shipping_address = forms.CharField(required=False)
    shipping_address2 = forms.CharField(required=False)
    shipping_country = CountryField(blank_label='(select country)').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100',
        }))
    shipping_zip = forms.CharField(required=False)
    use_default_shipping = forms.BooleanField(required=False)
    set_default_shipping = forms.BooleanField(required=False)
    payment_option = forms.ChoiceField(
        widget=forms.RadioSelect, choices=PAYMENT_CHOICES)

# class Payment(forms.Form):
#     stripeToken = forms.CharField(required=False)
#     # save = forms.BooleanField(required=False)
#     # use_default = forms.BooleanField(required=False)

class CouponForm(forms.Form):
    code = forms.CharField(widget=forms.TextInput(attrs= {
        'placeholder' : 'Enter Coupon Code',
        'class' : 'ml-2'
    }))

class RefundForm(forms.Form):
    ref_code = forms.CharField()
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea(attrs={
        'row' : 4
    }))

