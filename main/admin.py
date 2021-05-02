from django.contrib import admin
from .models import (
    Order,
    OrderItem,
    Item,
    Address,
    Payment,
    Coupon,
    Refund,
    PaymentViaPaytm,
)

# Register your models here.


def make_refund_accepted(modeladmin, request, queryset):
    queryset.update(refund_requested=False, refund_granted=True)


make_refund_accepted.short_description = "Update orders to refund granted"


class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "ordered",
        "order_status",
        "refund_requested",
        "refund_granted",
        "shipping_address",
        "payment",
    ]
    list_display_links = ["user", "shipping_address", "payment"]
    list_filter = ["ordered", "refund_requested", "refund_granted"]
    search_fields = ["user__username", "ref_code"]
    actions = [make_refund_accepted]


class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "ordered",
        "item",
    ]
    list_display_links = [
        "user",
        "ordered",
    ]
    search_fields = [
        "user__username",
    ]


admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Item)
admin.site.register(Address)
admin.site.register(Coupon)
admin.site.register(Payment)
admin.site.register(Refund)
admin.site.register(PaymentViaPaytm)