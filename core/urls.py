from django.urls import path, include
from . import views

app_name = "core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("product/<slug>", views.ProductDetailView.as_view(), name="product"),
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    path('add-to-cart/<slug>/', views.add_to_cart, name="add-to-cart"),
    path('remove-from-cart/<slug>/', views.remove_from_cart, name="remove-from-cart"),
    path('order-summary/', views.OrderSummary.as_view(), name="order-summary"),
    path('remove-item-from-cart/<slug>/', views.remove_single_item_from_cart, name="remove-single-item-from-cart"),
    path('payment/<payment_option>/', views.PaymentView.as_view(), name='payment'),
    path('add-coupon/', views.AddCouponView.as_view(), name="add-coupon"),
    path('request-refund/', views.RequestRefundView.as_view(), name="request-refund"),
    

]
