from django.urls import path
from . import views


urlpatterns = [
    path("", views.item_list, name="item_list"),
    path("product/", views.product, name="product"),
    path("check_out", views.check_out, name="check_out"),
]