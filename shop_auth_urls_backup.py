from django.urls import path
from . import views

app_name = 'shop_auth'

urlpatterns = [
    path('', views.register, name='register'),
]
