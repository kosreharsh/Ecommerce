from rest_framework import viewsets
from main.serializers import ItemSerializer, MyOrderSerializer
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from main.models import *
# api views
class ItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer

class MyOrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MyOrderSerializer
    authentication_class = [ BasicAuthentication]
    permission_class = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user.id 
        queryset = Order.objects.filter(user=user).order_by('-ordered_date')
        return queryset
