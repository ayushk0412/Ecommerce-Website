from django.urls import path
from .views import (
    HomeView,
    ItemDetailView,
    add_to_cart,
    remove_from_cart,
    OrderSummaryView,
    remove_single_item_from_cart,
    CheckoutView,
    PaymentLanding,
    CheckoutSession,
    PaymentSuccess,
    PaymentCancel,
    stripe_webhook
)

app_name = "core"

urlpatterns = [
    path('', HomeView.as_view(), name='item_list'),
    path('product/<slug>/', ItemDetailView.as_view(), name='product'),
    path('add-to-cart/<slug>/', add_to_cart, name="add-to-cart"),
    path('remove-from-cart/<slug>/',
         remove_from_cart, name="remove-from-cart"),
    path('remove-item-from-cart/<slug>/',
         remove_single_item_from_cart, name='remove-single-item-from-cart'),
    path('order-summary/', OrderSummaryView.as_view(), name='order-summary'),
    path('checkout/', CheckoutView.as_view(), name="checkout"),
    path('create-checkout-session',
         CheckoutSession.as_view(), name="create-checkout-session"),
    path('payment/<payment_option>/',
         PaymentLanding.as_view(), name="payment"),
    path('success/', PaymentSuccess.as_view(), name="payment-success"),
    path('cancel/', PaymentCancel.as_view(), name="payment-cancel"),
    path('webhook/stripe/', stripe_webhook, name='stripe-webhook'),
]
