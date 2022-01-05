from django.shortcuts import render, redirect, HttpResponse
from django.urls import reverse
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, View
from .models import (
    Item,
    OrderItem,
    Order,
    Address,
    Payment,
    Coupon,
    Refund,
    PaymentViaPaytm,
)
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone
from .forms import CheckOutForm, CouponForm, RefundForm

from .utils import paytm_gateway
from .Paytm.paytm_checksum import verify_checksum
from django.views.decorators.csrf import csrf_exempt
import stripe

import json
from django.db.models import Count


stripe.api_key = settings.STRIPE_SECRET_KEY
# `source` is obtained with Stripe.js; see https://stripe.com/docs/payments/accept-a-payment-charges#web-create-token


# views


def findorder(request):
    if request.order == None:
        try:
            order = Order.objects.get(user=request.user, ordered=False)
        except Order.DoesNotExist:
            ordered_date = timezone.now()
            order = Order.objects.create(
                user=request.user, ordered=False, ordered_date=ordered_date
            )
            order.save()
        request.session["order_id"] = order.id
        print("yes,order created")
        return order
    elif request.order.ordered == True:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered=False, ordered_date=ordered_date
        )
        request.session["order_id"] = order.id
        print("yes,order created")
        return order
    else:
        return request.order


class HomeView(ListView):
    model = Item
    paginate_by = 10

    def get(self, *args, **kwargs):
        ## checking order in request
        if self.request.user.is_authenticated:
            findorder(self.request)
        object_list = Item.objects.all().order_by("name")
        context = {
            "object_list": object_list,
            "allow_empty": True,
        }
        return render(self.request, "home-page.html", context)


class ProductDetail(DetailView):
    model = Item
    template_name = "product-page.html"

    def get(self, *args, **kwargs):
        ## checking order in request
        if self.request.user.is_authenticated:
            findorder(self.request)
        item = Item.objects.get(slug=kwargs["slug"])
        context = {
            "object": item,
        }
        return render(self.request, "product-page.html", context)


class PaymentView(View):
    def get(self, *args, **kwargs):
        order = self.request.order
        context = {
            "order": order,
            "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLISHABLE_KEY,
            "DISPLAY_COUPON_FORM": False,
        }
        return render(self.request, "payment-page.html", context)

    def post(self, *args, **kwargs):
        order = self.request.order
        amount = int(order.get_final_amount() * 100)
        try:
            token = self.request.POST.get("stripeToken")
            payment_intent = stripe.PaymentIntent.create(
                amount=1099,
                currency="inr",
                payment_method_types=["card"],
                receipt_email="jenny.rosen@example.com",
            )
            customer = stripe.Customer.create(
                name="Jenny Rosen",
                address={
                    "line1": "510 Townsend St",
                    "postal_code": "98140",
                    "city": "San Francisco",
                    "state": "CA",
                    "country": "US",
                },
            )
            payment = Payment()
            payment.stripe_charge_id = payment_intent["id"]
            payment.user = self.request.user
            payment.amount = order.get_final_amount()
            payment.save()

            order_item = order.items.all()
            order_item.update(ordered=True)
            for item in order_item:
                item.save()

            order.ordered = True
            order.payment = payment
            order.save()

            messages.success(self.request, "Your Payment was Successfull")
            return redirect("main:home")

        except stripe.error.CardError as e:
            body = e.json_body
            err = body.get("error", {})
            messages.warning(self.request, f"{err.get('message')}")
            print("hello")
            return redirect("main:home")

        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.warning(self.request, "Rate limit error")
            return redirect("main:home")

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            print(e)
            messages.warning(self.request, "Invalid parameters")
            return redirect("main:home")

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.warning(self.request, "Not authenticated")
            return redirect("main:home")

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.warning(self.request, "Network error")
            return redirect("main:home")

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.warning(
                self.request,
                "Something went wrong. You were not charged. Please try again.",
            )
            return redirect("main:home")

        except Exception as e:
            # send an email to ourselves
            messages.warning(
                self.request, "A serious error occurred. We have been notifed."
            )
            return redirect("main:home")

        messages.warning(self.request, "Invalid data received")
        return redirect("main:home")


class CheckOut(View):
    def get(self, *args, **kwargs):
        order = self.request.order
        form = CheckOutForm()
        coupon_form = CouponForm()
        display_coupon_form = True
        if order.coupon.all().count() != 0:
            display_coupon_form = False
        context = {
            "form": form,
            "order": order,
            "couponform": coupon_form,
            "DISPLAY_COUPON_FORM": display_coupon_form,
        }
        shipping_address_qs = Address.objects.filter(
            user=self.request.user, use_default_shipping=True
        )
        if shipping_address_qs.exists():
            context.update(
                {
                    "shipping_address": shipping_address_qs[0],
                    "default_address": True,
                }
            )
        return render(self.request, "checkout-page.html", context)

    def post(self, *args, **kwargs):
        form = CheckOutForm(self.request.POST or None)
        try:
            order = self.request.order
            if form.is_valid():
                use_default_shipping = form.cleaned_data.get("use_default_shipping")
                if use_default_shipping:
                    address = Address.objects.filter(
                        user=self.request.user, use_default_shipping=True
                    )[0]
                    shipping_address = address
                    order.shipping_address = shipping_address
                    order.save()
                else:
                    shipping_address1 = form.cleaned_data.get("shipping_address")
                    shipping_address2 = form.cleaned_data.get("shipping_address2")
                    shipping_country = form.cleaned_data.get("shipping_country")
                    shipping_zip = form.cleaned_data.get("shipping_zip")
                    set_default_shipping = form.cleaned_data.get("set_default_shipping")

                    shipping_address = Address(
                        user=self.request.user,
                        street_address=shipping_address1,
                        apartment_address=shipping_address2,
                        country=shipping_country,
                        zipcode=shipping_zip,
                    )
                    if set_default_shipping:
                        shipping_address.use_default_shipping = True
                    shipping_address.save()
                    order.shipping_address = shipping_address
                    order.save()

                payment_choice = form.cleaned_data.get("payment_option")
                if payment_choice == "S":
                    return redirect("main:payment", payment_option="stripe")
                elif payment_choice == "P":
                    paytm_params = paytm_gateway(
                        order_id=order.id, user_id=self.request.user.id
                    )

                    return render(self.request, "redirect.html", context=paytm_params)
            else:
                messages.error(self.request, "Enter valid address")
                return redirect("main:checkout")
        except ObjectDoesNotExist:
            messages.warning(self.request, "Error!!!")
            redirect("main:checkout")


@csrf_exempt
def PaytmCallback(request):
    if request.method == "POST":
        received_data = dict(request.POST)
        paytm_params = {}
        paytm_checksum = received_data["CHECKSUMHASH"][0]
        for key, value in received_data.items():
            if key == "CHECKSUMHASH":
                paytm_checksum = value[0]
            else:
                paytm_params[key] = str(value[0])
        is_valid_checksum = verify_checksum(
            paytm_params, settings.PAYTM_SECRET_KEY, str(paytm_checksum)
        )
        if is_valid_checksum:
            received_data["message"] = "CHECKSUM_MATCHED"
        else:
            received_data["message"] = "CHECKSUM_MISMATCHED"

        if str(received_data["RESPCODE"][0]) == "01":

            order_id = received_data["ORDERID"][0]
            id = order_id.split("_")
            payment = PaymentViaPaytm.objects.get(order_id=order_id)
            try:
                order = Order.objects.get(id=id[0])
                order_item = order.items.all()
                order_item.update(ordered=True)
                for item in order_item:
                    item.save()
                order.payment_via_paytm = payment
                order.ordered = True
                order.save()
            except ObjectDoesNotExist:
                messages.warning(request, "Order Not Found")
        return render(request, "callback_response.html", context=received_data)


class OrderSummary(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            findorder(self.request)
        order = self.request.order
        context = {"object": order}
        return render(self.request, "order_summary.html", context)


def add_to_cart(request, slug):
    if not request.user.is_authenticated:
        messages.info(request, "Login to put item into cart")
        return redirect("main:product-detail", slug=slug)
    order = request.order

    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item, user=request.user, ordered=False
    )
    if not created:
        order_item.quantity += 1
        order_item.save()
        messages.info(request, "This item quantity updated in your cart")
        return redirect("main:order-summary")
    else:
        order.items.add(order_item)
        messages.info(request, "This item are added in your cart")
        return redirect("main:product-detail", slug=slug)


def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order = request.order
    if order.items.filter(item__slug=item.slug).exists():
        order_item = OrderItem.objects.filter(
            item=item, user=request.user, ordered=False
        )[0]
        if order_item.quantity > 1:
            order_item.quantity -= 1
            order_item.save()
            messages.info(request, "This item quantity is updated")
            if order.items.count() == 0:
                return redirect("/")
            return redirect("main:order-summary")
        else:
            order.items.remove(order_item)
            order_item.delete()
            messages.info(request, "Item is removed from your cart")
            if order.items.count() == 0:
                return redirect("/")
            return "main:order-summary"
    else:
        messages.info(request, "This item was not in your cart")
        return redirect("main:product-detail", slug=slug)


def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order = request.order
    if order.items.filter(item__slug=item.slug).exists():
        order_item = OrderItem.objects.filter(
            item=item, user=request.user, ordered=False
        )[0]
        order.items.remove(order_item)
        order_item.delete()
        if order.items.count() == 0:
            return redirect("/")
        return redirect("main:order-summary")
    else:
        messages.info(request, "This item was removed from your cart")
        if order.items.count() == 0:
            return redirect("/")
        return redirect("main:order-summary")


def add_coupon(request):
    order = request.order
    response_data = {}
    if request.method == "POST":
        form = CouponForm(request.POST or None)
        if form.is_valid():
            code = form.cleaned_data.get("code")
            print(code)
            try:
                coupon = Coupon.objects.get(code=code)
                print(coupon.code)
                order.coupon.add(coupon)
                order.save()
                response_data["message"] = "sucessfull"
                response_data["code"] = coupon.code
                response_data["amount"] = coupon.amount

                return HttpResponse(
                    json.dumps(response_data), content_type="application/json"
                )
            except ObjectDoesNotExist:

                return HttpResponse(
                    json.dumps({"nothing to see": "this isn't happening"}),
                    content_type="application/json",
                )
        else:

            return HttpResponse(
                json.dumps({"nothing to see": "this isn't happening"}),
                content_type="application/json",
            )


class RefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {"form": form}
        return render(self.request, "refund-page.html", context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST or None)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            message = form.cleaned_data.get("message")
            ref_code = form.cleaned_data.get("ref_code")
            try:
                order = Order.objects.get(ref_code=ref_code)
                refund = Refund.objects.create(
                    order=order,
                    email=email,
                    reason=message,
                )
                order.refund_requested = True
                order.save()
                messages.info(self.request, "Your request was received.")
                return redirect("main:refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist.")
                return redirect("main:refund")


class OrderStatus(DetailView, LoginRequiredMixin):
    model = Order
    template_name = "order-status.html"

    def get_object(self, queryset=None):
        return Order.objects.get(ref_code=self.kwargs.get("ref_code"))


class OrderListView(ListView, LoginRequiredMixin):
    model = Order

    def get(self, *args, **kwargs):
        object_list = Order.objects.filter(user=self.request.user).order_by(
            "-ordered_date"
        )

        context = {
            "object_list": object_list,
            "allow_empty": True,
        }
        return render(self.request, "myorderlist-page.html", context)
