"""Ecommerce URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import debug_toolbar
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path,include
from django.conf import settings
from decouple import config
from rest_framework import routers
from main.api.views import ItemViewSet, MyOrderViewSet

router = routers.DefaultRouter()
router.register('items', ItemViewSet , basename='item')
router.register('myorder', MyOrderViewSet , basename="myorder")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/',include(router.urls)),
    path('accounts/', include('allauth.urls')),
    path('',include('main.urls',namespace='main')), 
    path('api-auth/', include('rest_framework.urls')),

] 

if config('DEBUG'):
    urlpatterns += path('__debug__/', include(debug_toolbar.urls)),
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)


