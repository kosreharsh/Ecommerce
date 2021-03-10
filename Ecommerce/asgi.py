import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
import django
from channels.http import AsgiHandler
import main.routing
os.environ.setdefault('DJANGO_SETTINGS_MODULE','Ecommerce.settings')
django.setup()



application= ProtocolTypeRouter(
    {
        'http': AsgiHandler(),
        'websocket': AuthMiddlewareStack(
            URLRouter(
                main.routing.websocket_urlpattern
            )
        ),
    }
)