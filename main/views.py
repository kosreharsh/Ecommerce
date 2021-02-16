from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView,DetailView, View
from .models import Item,OrderItem,Order, Address, Payment, Coupon, Refund, PaymentViaPaytm
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone
from .forms import CheckOutForm, CouponForm, RefundForm
from .Paytm.paytm_checksum import generate_checksum ,verify_checksum
from django.views.decorators.csrf import csrf_exempt
import stripe
import random, string




stripe.api_key = settings.STRIPE_SECRET_KEY
# `source` is obtained with Stripe.js; see https://stripe.com/docs/payments/accept-a-payment-charges#web-create-token

def create_ref(k):
    return ''.join(random.choices(string.ascii_lowercase+string.ascii_uppercase, k=20))

class HomeView(ListView):
    model = Item 
    paginate_by = 10
    template_name = 'home-page.html'

    def get_queryset(self):
        queryset = Item.objects.all().order_by('name')
        return queryset
    
class ProductDetail(DetailView):
    model = Item
    template_name = 'product-page.html'

# class PaymentViewForPaytm(View):
#     def get(self, *args, **kwargs):
#         order = Order.objects.get(user= self.request.user, ordered=False)
#         context = {
#             'order': order,
#         }
#         return render(self.request, 'paytm-payment-page.html',context)
    
#     def post(self, *args, **kwargs):
#         order = Order.objects.get(user= self.request.user, ordered=False)
#         amount = order.get_final_amount()

#         params = (
#         ('MID', settings.PAYTM_MERCHANT_ID),
#         ('ORDER_ID', str(order.id)),
#         ('CUST_ID', str(self.request.user.username)),
#         ('TXN_AMOUNT', str(amount)),
#         ('CHANNEL_ID', settings.PAYTM_CHANNEL_ID),
#         ('WEBSITE', settings.PAYTM_WEBSITE),
#         ('INDUSTRY_TYPE_ID', settings.PAYTM_INDUSTRY_TYPE_ID),
#         ('CALLBACK_URL', 'http://127.0.0.1:8000/callback/'),
#     )
#     paytm_params = dict(params)
#     checksum = generate_checksum(paytm_params, merchant_key)
#     payment = PaymentViaPaytm.objects.create(user=self.request.user,order_id = order.id,amount=amount,checksum=checksum)

#     paytm_params['CHECKSUMHASH'] = checksum
#     return render(request, 'payment/redirect.html', context=paytm_params)

class PaymentView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user= self.request.user, ordered=False)
        context = {
            'order': order,
            'STRIPE_PUBLIC_KEY' : settings.STRIPE_PUBLISHABLE_KEY ,
            'DISPLAY_COUPON_FORM' : False,
        }
        return render(self.request, 'payment-page.html',context)
    
    def post(self, *args, **kwargs):
        order = Order.objects.get(user= self.request.user, ordered=False)
        amount = int(order.get_final_amount()*100)
        try:
            token = self.request.POST.get('stripeToken')
            payment_intent = stripe.PaymentIntent.create(
                amount=1099,
                currency='inr',
                payment_method_types=['card'],
                receipt_email='jenny.rosen@example.com',
            )
            customer=stripe.Customer.create(
                name='Jenny Rosen',
                address={
                    'line1': '510 Townsend St',
                    'postal_code': '98140',
                    'city': 'San Francisco',
                    'state': 'CA',
                    'country': 'US',
                },
                
            )
           
            

            payment = Payment()
            payment.stripe_charge_id = payment_intent['id']
            payment.user = self.request.user
            payment.amount = order.get_final_amount()
            payment.save()

            order_item = order.items.all()
            order_item.update(ordered=True)
            for item in order_item:
                item.save()

            order.ordered=True
            order.payment= payment
            order.ref_code = create_ref(20)
            order.save()

            messages.success(self.request,'Your Payment was Successfull')
            return redirect('main:home')

        except stripe.error.CardError as e:
                body = e.json_body
                err = body.get('error', {})
                messages.warning(self.request, f"{err.get('message')}")
                print('hello')
                return redirect('main:home')

        except stripe.error.RateLimitError as e:
                # Too many requests made to the API too quickly
                messages.warning(self.request, "Rate limit error")
                return redirect('main:home')

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
                print(e)
                messages.warning(self.request, "Invalid parameters")
                return redirect('main:home')

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
                messages.warning(self.request, "Not authenticated")
                return redirect('main:home')

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
                messages.warning(self.request, "Network error")
                return redirect('main:home')

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
                messages.warning(self.request, "Something went wrong. You were not charged. Please try again.")
                return redirect('main:home')

        except Exception as e:
            # send an email to ourselves
                messages.warning(self.request, "A serious error occurred. We have been notifed.")
                return redirect('main:home')

        messages.warning(self.request, "Invalid data received")
        return redirect('main:home')

class CheckOut(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user,ordered=False)
        form = CheckOutForm()
        coupon_form= CouponForm()
        context = {
            'form' : form,
            'order' : order,
            'couponform' : coupon_form,
            'DISPLAY_COUPON_FORM' : True ,
        }
        shipping_address_qs = Address.objects.filter(user=self.request.user, use_default_shipping=True)
        if shipping_address_qs.exists():
            context.update({'shipping_address' : shipping_address_qs[0] , 'default_address' : True ,})
        return render(self.request,'checkout-page.html', context)
    
    def post(self, *args, **kwargs):
        form = CheckOutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user,ordered=False)
            if form.is_valid():
                use_default_shipping = form.cleaned_data.get('use_default_shipping')
                if use_default_shipping:
                    address_qs = Address.objects.filter(user=self.request.user, use_default_shipping=True)
                    if address_qs.exists():
                        shipping_address = address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else :
                        message.warning(self.request, " Default Address not found!!!")
                        return redirect('main:checkout')
                else:
                    shipping_address1 = form.cleaned_data.get('shipping_address')
                    shipping_address2 = form.cleaned_data.get('shipping_address2')
                    shipping_country = form.cleaned_data.get('shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')
                    set_default_shipping = form.cleaned_data.get('set_default_shipping')

                    shipping_address = Address(
                        user=self.request.user,
                        street_address=shipping_address1,
                        apartment_address=shipping_address2,
                        country=shipping_country,
                        zipcode=shipping_zip,   
                    )
                    if set_default_shipping:
                        shipping_address.use_default_shipping=True
                    shipping_address.save()
                    order.shipping_address = shipping_address
                    order.save()

                payment_choice = form.cleaned_data.get('payment_option')
                if payment_choice == 'S':
                    return redirect('main:payment',payment_option='stripe')
                elif payment_choice == 'P':
                    amount = order.get_final_amount()
                    order_id = str(order.id) + '_' + create_ref(20)
                    merchant_key = settings.PAYTM_SECRET_KEY
                    params = (
                        ('MID', settings.PAYTM_MERCHANT_ID),
                        ('ORDER_ID', str(order_id)),
                        ('CUST_ID', str(self.request.user.username)),
                        ('TXN_AMOUNT', str(amount)),
                        ('CHANNEL_ID', settings.PAYTM_CHANNEL_ID),
                        ('WEBSITE', settings.PAYTM_WEBSITE),
                        ('INDUSTRY_TYPE_ID', settings.PAYTM_INDUSTRY_TYPE_ID),
                        ('CALLBACK_URL', 'http://127.0.0.1:8000/payment_confirmation/'),
                    )
                    paytm_params = dict(params)
                    checksum = generate_checksum(paytm_params, merchant_key)
                    payment = PaymentViaPaytm.objects.create(user=self.request.user,order_id = order_id,amount=amount,checksum=checksum)

                    paytm_params['CHECKSUMHASH'] = checksum
                    return render(self.request, 'redirect.html', context=paytm_params)
            else:
                messages.error(self.request,'Enter valid address')  
                return redirect('main:checkout')
        except ObjectDoesNotExist :
            messages.warning(self.request,'Error!!!')
            redirect('main:checkout')

@csrf_exempt
def PaytmCallback(request):
    if request.method == 'POST':
        received_data = dict(request.POST)
        paytm_params = {}
        paytm_checksum = received_data['CHECKSUMHASH'][0]
        for key, value in received_data.items():
            if key == 'CHECKSUMHASH':
                paytm_checksum = value[0]
            else:
                paytm_params[key] = str(value[0])
        is_valid_checksum = verify_checksum(paytm_params, settings.PAYTM_SECRET_KEY, str(paytm_checksum))
        if is_valid_checksum:
            received_data['message'] = 'CHECKSUM_MATCHED'
        else:
            received_data['message'] = 'CHECKSUM_MISMATCHED'
        
        if str(received_data['RESPCODE'][0]) == '01':
           
            order_id=received_data['ORDERID'][0]
            id=order_id.split('_')
            payment = PaymentViaPaytm.objects.get(order_id=order_id)
            try:
                order = Order.objects.get(id=id[0])
                order_item = order.items.all()
                order_item.update(ordered=True)
                for item in order_item:
                    item.save()
                order.ref_code = id[1]
                order.payment_via_paytm = payment
                order.ordered=True
                order.save()
            except ObjectDoesNotExist :
                message.warning(request,'Order Not Found')
        return render(request, 'callback_response.html', context=received_data)

class OrderSummary(LoginRequiredMixin,View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user= self.request.user , ordered= False)
            context = {
                'object' : order
            }
            
            return render(self.request,'order_summary.html', context )
        except ObjectDoesNotExist :
            messages.warning(self.request, "You do not have an active order")
            return redirect("/")

def add_to_cart(request,slug):
    
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item = item,
        user = request.user,
        ordered= False
    )
    
    order_qs = Order.objects.filter( user=request.user,ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity +=1
            order_item.save()
            messages.info(request, "This item quantity updated in your cart")
            return redirect('main:order-summary')
        else:
            order.items.add(order_item)
            messages.info(request, "This item are added in your cart")
            return redirect('main:product-detail',slug= slug)
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user,
            ordered_date=ordered_date,
        )
        order.items.add(order_item)
        messages.info(request, "This item are added in your cart")
        return redirect('main:product-detail',slug=slug)

def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter( user=request.user,ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item = item,
                user = request.user,
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
                messages.info(request, "This item quantity is updated")
                if order.items.count() == 0:
                    return redirect('/')
                return redirect('main:order-summary')
            else:
                order.items.remove(order_item)
                order_item.delete()
                messages.info(request, "Item is removed from your cart")
                if order.items.count() == 0:
                    return redirect('/')
                return('main:order-summary')
    else:
        messages.info(request, "This item was not in your cart")
        return redirect('main:product-detail',slug=slug)

def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter( user=request.user,ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item = item,
                user = request.user,
            )[0]
            order.items.remove(order_item)
            order_item.delete()
            if order.items.count() == 0:
                    return redirect('/')
            return redirect('main:order-summary')
        else:
            messages.info(request, "This item was not in your cart")
            if order.items.count() == 0:
                    return redirect('/')
            return redirect('main:order-summary')
    else:
        messages.info(request, "This item was not in your cart")
        return redirect('main:product-detail',slug=slug)

def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.warning(request,'Coupon does not exist')
        return redirect('main:checkout')

def add_coupon(request):
    if request.method == 'POST': 
        try:
            form = CouponForm(request.POST or None)
            if form.is_valid():
                code = form.cleaned_data.get('code')
                order = Order.objects.get(user=request.user,ordered=False)
                order.coupon = get_coupon(request,code)
                order.save()
                messages.success(request,'Coupon is applied Successfully')
                return redirect('main:checkout')
        except ObjectDoesNotExist:
            messages.warning(request,'Coupon does not exist')
            return redirect('main:checkout')

class RefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form' : form
        }
        return render(self.request,'refund-page.html', context)
    
    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST or None)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            message = form.cleaned_data.get('message')
            ref_code = form.cleaned_data.get('ref_code')
            try:
                order = Order.objects.get(ref_code=ref_code)
                refund = Refund.objects.create(
                    order = order,
                    email=email,
                    reason = message,
                    
                )
                order.refund_requested = True
                order.save()
                messages.info(self.request, "Your request was received.")
                return redirect("main:refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist.")
                return redirect("main:refund")
