from .Paytm.paytm_checksum import generate_checksum, verify_checksum
from .models import PaymentViaPaytm, Order
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


def paytm_gateway(order_id, user_id):
    order = Order.objects.get(id=order_id)
    user = User.objects.get(id=user_id)
    amount = order.get_final_amount()
    order_id = str(order.id) + "_" + order.ref_code
    merchant_key = settings.PAYTM_SECRET_KEY
    params = (
        ("MID", settings.PAYTM_MERCHANT_ID),
        ("ORDER_ID", str(order_id)),
        ("CUST_ID", str(user.username)),
        ("TXN_AMOUNT", str(amount)),
        ("CHANNEL_ID", settings.PAYTM_CHANNEL_ID),
        ("WEBSITE", settings.PAYTM_WEBSITE),
        ("INDUSTRY_TYPE_ID", settings.PAYTM_INDUSTRY_TYPE_ID),
        ("CALLBACK_URL", "http://127.0.0.1:8000/payment_confirmation/"),
    )
    paytm_params = dict(params)
    checksum = generate_checksum(paytm_params, merchant_key)
    payment = PaymentViaPaytm.objects.create(
        user=user,
        order_id=order_id,
        amount=amount,
        checksum=checksum,
    )

    paytm_params["CHECKSUMHASH"] = checksum
    return paytm_params


def paytm_gateway_for_frontend(order_id, user_id):
    order = Order.objects.get(id=order_id)
    user = User.objects.get(id=user_id)
    amount = order.get_final_amount()
    order_id = str(order.id) + "_" + order.ref_code
    merchant_key = settings.PAYTM_SECRET_KEY
    params = (
        ("MID", settings.PAYTM_MERCHANT_ID),
        ("ORDER_ID", str(order_id)),
        ("CUST_ID", str(user.username)),
        ("TXN_AMOUNT", str(amount)),
        ("CHANNEL_ID", settings.PAYTM_CHANNEL_ID),
        ("WEBSITE", settings.PAYTM_WEBSITE),
        ("INDUSTRY_TYPE_ID", settings.PAYTM_INDUSTRY_TYPE_ID),
        ("CALLBACK_URL", "http://localhost:3000/payment-status/"),
    )
    paytm_params = dict(params)
    checksum = generate_checksum(paytm_params, merchant_key)
    payment = PaymentViaPaytm.objects.create(
        user=user,
        order_id=order_id,
        amount=amount,
        checksum=checksum,
    )

    paytm_params["CHECKSUMHASH"] = checksum
    return paytm_params