from django.urls import path
from .consumers import OrderProgress
websocket_urlpattern = [
    path('ws/status/<int:order_id>/', OrderProgress.as_asgi()),
]