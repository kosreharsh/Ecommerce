from rest_framework import serializers
from .models import Item, Order , Address, OrderItem

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = [ 'id', 'name','price','discount_price','category','label','description','slug' ]

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [ 'id' ,'street_address','apartment_address','country','zipcode']

class OrderItemSerializer(serializers.ModelSerializer):
    item = ItemSerializer(read_only=True)
    class Meta:
        model = OrderItem
        fields = [ 'id','item','quantity']

class MyOrderSerializer(serializers.ModelSerializer):
    shipping_address = AddressSerializer(read_only=True)
    user = serializers.StringRelatedField()
    items = OrderItemSerializer(many=True,read_only=True)
    class Meta:
        model = Order
        fields = [ 'id' , 'user','ref_code','items', 'ordered','ordered_date','shipping_address','coupon','payment', 'payment_via_paytm']