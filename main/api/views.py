from rest_framework import viewsets, status, decorators, permissions
from main.serializers import (
    ItemSerializer,
    MyOrderSerializer,
    OrderItemSerializer,
    AddressSerializer,
    UserCreateSerializer,
    PaytmParamsSerializer,
)
from rest_framework.authentication import BasicAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from main.models import *
import io
from rest_framework.parsers import JSONParser
import json
from ..utils import paytm_gateway_for_frontend

# api views
@decorators.api_view(["post"])
@decorators.permission_classes([permissions.AllowAny])
def registration(request):
    serializer = UserCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    print(serializer.validated_data)
    serializer.save()
    return Response(
        {"msg": "user created successfully."}, status=status.HTTP_201_CREATED
    )


@decorators.api_view(["post"])
@decorators.permission_classes([permissions.IsAuthenticated])
def get_paytm_creditionals(request):
    order_id = request.data.get("order_id")
    if not order_id:
        return Response({"msg": "order id not specified"})
    user_id = request.user.id

    params = paytm_gateway_for_frontend(order_id, user_id)
    paytm_params = PaytmParams(
        MID=params["MID"],
        ORDER_ID=params["ORDER_ID"],
        CUST_ID=params["CUST_ID"],
        TXN_AMOUNT=params["TXN_AMOUNT"],
        CHANNEL_ID=params["CHANNEL_ID"],
        WEBSITE=params["WEBSITE"],
        INDUSTRY_TYPE_ID=params["INDUSTRY_TYPE_ID"],
        CALLBACK_URL=params["CALLBACK_URL"],
        CHECKSUMHASH=params["CHECKSUMHASH"],
    )
    serializer = PaytmParamsSerializer(paytm_params)
    return Response(serializer.data)


class ItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    permission_class = [AllowAny]


class MyOrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MyOrderSerializer
    authentication_class = [TokenAuthentication]
    permission_class = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user.id
        queryset = Order.objects.filter(user=user).order_by("-ordered_date")
        return queryset

    @action(detail=False, methods=["GET"])
    def get_current_order(self, request):
        obj = Order.objects.filter(user=self.request.user, ordered=False)[0]
        serializer = MyOrderSerializer(obj)
        return Response(serializer.data)

    @action(detail=True, methods=["POST"])
    def add_address(self, request, pk):
        Aid = request.data.get("id")
        obj = self.get_object()
        address = Address.objects.filter(user=self.request.user, id=Aid)[0]
        obj.shipping_address = address
        obj.save()
        return Response({"msg": "Address added successfully", "order_id": obj.id})


class CurrentCartViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    authentication_class = [TokenAuthentication]
    permission_class = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user.id
        queryset = OrderItem.objects.filter(user=user, ordered=False)
        return queryset

    @action(detail=False, methods=["post"])
    def addItem(self, request, id=None):
        data = request.data
        try:
            item_id = data.get("id")
            qs = self.get_queryset()
            for i in qs:
                if i.item.id == item_id:
                    return Response(
                        {"msg": "Item is already in the cart."},
                        status=status.HTTP_201_CREATED,
                    )
            item = Item.objects.get(pk=item_id)
            new_OrderItem = OrderItem.objects.create(item=item, user=self.request.user)
            new_OrderItem.save()
            oqs = Order.objects.filter(user=self.request.user, ordered=False)
            if oqs.exists():
                order = oqs[0]
                order.items.add(new_OrderItem)
                order.save()
                return Response(
                    {"msg": "Item added into the Cart"}, status=status.HTTP_201_CREATED
                )
            else:
                new_order = Order.objects.create(user=self.request.user)
                new_order.items.add(new_OrderItem)
                new_order.save()
                return Response(
                    {"msg": "Item added into the Cart"}, status=status.HTTP_201_CREATED
                )

        except Item.DoesNotExist:
            return Response(
                {"msg": "Item not found"}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def removeItem(self, request):
        data = request.data
        try:
            orderitem_id = data.get("id")
            orderitem = OrderItem.objects.get(pk=orderitem_id)
            qs = self.get_queryset()
            if not orderitem in qs:
                return Response(
                    {"msg": "Item not found in the cart."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            oqs = Order.objects.filter(user=self.request.user, ordered=False)
            if oqs.exists():
                order = oqs[0]
                order.items.remove(orderitem)
                order.save()
                orderitem.delete()
                return Response({"msg": "Item removed"}, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"msg": "Item not found"}, status=status.HTTP_400_BAD_REQUEST
                )
        except OrderItem.DoesNotExist:
            return Response({"msg": "Item not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=["post"])
    def updateQuantity(self, request):
        data = request.data

        try:

            item_id = int(data.get("id"))
            quantity = int(data.get("quantity"))
            if quantity < 0:
                return Response({"msg": "Quantity is negative"})

            qs = self.get_queryset()
            for i in qs:
                if i.item.id == item_id:
                    i.quantity = quantity
                    if i.quantity == 0:
                        order = Order.objects.filter(
                            user=self.request.user, ordered=False
                        )[0]
                        order.items.remove(i)
                        order.save()
                        i.delete()
                        return Response(
                            {"msg": "Item removed from the cart"},
                            status=status.HTTP_201_CREATED,
                        )
                    else:
                        i.save()
                        return Response(
                            {"msg": "Item quantity updated"},
                            status=status.HTTP_201_CREATED,
                        )
            return Response(
                {"msg": "Item not found in the cart."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Item.DoesNotExist:
            return Response(
                {"msg": "Item not found"}, status=status.HTTP_400_BAD_REQUEST
            )


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    authentication_class = [TokenAuthentication]
    permission_class = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user.id
        queryset = Address.objects.filter(user=user)
        return queryset

    def perform_create(self, serializer):
        print(self.request.user)
        serializer.save(user=self.request.user)
