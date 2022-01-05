from rest_framework import serializers
from .models import Item, Order, Address, OrderItem, PaytmParams
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()


class PaytmParamsSerializer(serializers.Serializer):
    MID = serializers.CharField()
    ORDER_ID = serializers.CharField()
    CUST_ID = serializers.CharField()
    TXN_AMOUNT = serializers.CharField()
    CHANNEL_ID = serializers.CharField()
    WEBSITE = serializers.CharField()
    INDUSTRY_TYPE_ID = serializers.CharField()
    CALLBACK_URL = serializers.URLField()
    CHECKSUMHASH = serializers.CharField()


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        style={
            "input_type": "password",
        },
    )
    password2 = serializers.CharField(
        write_only=True,
        style={
            "input_type": "password",
            "label": "Confirm Password",
        },
    )

    def validate(self, data):
        if User.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError(
                {"email": "Email Address should be unique"}
            )
        if data["password"] != data["password2"]:
            raise serializers.ValidationError({"password": "Password does not match."})
        return data

    def create(self, validated_data):
        username = validated_data["username"]
        email = validated_data["email"]
        password = validated_data["password"]
        user = User.objects.create(username=username, email=email)
        user.set_password(password)
        user.save()
        return user

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "password2",
        ]
        extra_kwargs = {
            "password": {
                "required": True,
                "write_only": True,
            },
            "password2": {
                "required": True,
            },
        }


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = [
            "id",
            "name",
            "price",
            "discount_price",
            "category",
            "label",
            "description",
            "slug",
        ]


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id",
            "street_address",
            "apartment_address",
            "country",
            "zipcode",
            "use_default_shipping",
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    item = ItemSerializer(read_only=True)
    quantity = serializers.CharField(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "item", "quantity"]


class MyOrderSerializer(serializers.ModelSerializer):
    shipping_address = AddressSerializer(read_only=True)
    user = serializers.StringRelatedField()
    items = OrderItemSerializer(many=True, read_only=True)
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "ref_code",
            "total_amount",
            "items",
            "ordered",
            "ordered_date",
            "shipping_address",
            # "coupon",
            "payment",
            "payment_via_paytm",
        ]

    def get_total_amount(self, obj):
        return obj.get_final_amount()
