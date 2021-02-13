from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView,DetailView, View
# Create your views here.
from .models import Item,OrderItem,Order, Address, Payment, Coupon, Refund
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .forms import CheckOutForm, CouponForm, RefundForm
import stripe
from django.conf import settings
import random, string
# stripe.api_key = settings.STRIPE_SECRET_KEY

stripe.api_key = settings.STRIPE_SECRET_KEY
# `source` is obtained with Stripe.js; see https://stripe.com/docs/payments/accept-a-payment-charges#web-create-token

def create_ref():
    return ''.join(random.choices(string.ascii_lowercase+string.ascii_uppercase, k=20))


class HomeView(ListView):
    model = Item 
    paginate_by = 10
    template_name = 'home-page.html'
    

class ProductDetail(DetailView):
    model = Item
    template_name = 'product-page.html'

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
            order.ref_code = create_ref()
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
        return render(self.request,'checkout-page.html', context)
    
    def post(self, *args, **kwargs):
        form = CheckOutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user,ordered=False)
            if form.is_valid():
                shipping_address1 = form.cleaned_data.get('shipping_address')
                shipping_address2 = form.cleaned_data.get('shipping_address2')
                shipping_country = form.cleaned_data.get('shipping_country')
                shipping_zip = form.cleaned_data.get('shipping_zip')

                shipping_address = Address(
                    user=self.request.user,
                    street_address=shipping_address1,
                    apartment_address=shipping_address2,
                    country=shipping_country,
                    zipcode=shipping_zip,
                    
                )
                shipping_address.save()
                order.shipping_address = shipping_address
                order.save()

                payment_choice = form.cleaned_data.get('payment_option')
                if payment_choice == 'S':
                    return redirect('main:payment',payment_option='stripe')
                messages.error(self.request,'Choose correct payment option')  
                return redirect('main:checkout')
        except ObjectDoesNotExist :
            messages.warning(self.request,'Error!!!')
            redirect('main:checkout')


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
            return reverse('main:product_detail',kwargs={ 'slug' : slug })
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user,
            ordered_date=ordered_date,
        )
        order.items.add(order_item)
        messages.info(request, "This item are added in your cart")
        return redirect('main:product_detail',slug=slug)


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
                return redirect('main:order-summary')
            else:
                order.items.remove(order_item)
                order_item.delete()
                messages.info(request, "Item is removed from your cart")
                return('main:order-summary')
    else:
        messages.info(request, "This item was not in your cart")
        return redirect('main:product_detail',slug=slug)

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
            return redirect('main:order-summary')
        else:
            messages.info(request, "This item was not in your cart")
            return redirect('main:order-summary')
    else:
        messages.info(request, "This item was not in your cart")
        return redirect('main:product_detail',slug=slug)

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
