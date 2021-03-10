from django.urls import path,include
from .views import (
    HomeView,
    ProductDetail,
    add_to_cart,
    remove_from_cart,
    OrderSummary,
    remove_single_item_from_cart,
    CheckOut,
    PaymentView,
    add_coupon,
    RefundView,
    PaytmCallback,
    OrderListView,
    OrderStatus,
    )

app_name = 'main'



urlpatterns = [
    
    path('', HomeView.as_view(), name='home'),
    path('myorder/',OrderListView.as_view(), name='myorderlist'),
    path('product/<slug>', ProductDetail.as_view(),name='product-detail'),
    path('add_to_cart/<slug>',add_to_cart,name='add-to-cart'),
    path('remove_from_cart/<slug>',remove_from_cart,name='remove-from-cart'),
    path('remove_single_item_from_cart/<slug>',remove_single_item_from_cart,name='remove-single-item-from-cart'),
    path('order_summary/', OrderSummary.as_view(),name='order-summary'),
    path('payment/<payment_option>/', PaymentView.as_view(),name='payment'),
    path('checkout/', CheckOut.as_view(),name='checkout'),
    path('add_coupon/', add_coupon ,name='add-coupon'),
    path('refund/', RefundView.as_view() ,name='refund'),
    path('payment_confirmation/', PaytmCallback ,name='paytm-confirmation'),
    path('order_status/<str:ref_code>',OrderStatus.as_view(),name='orderStatus'),
    

]