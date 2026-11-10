from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CarViewSet, purchase_request, rental_booking, stripe_webhook

router = DefaultRouter()
router.register("cars", CarViewSet, basename="car")

urlpatterns = [
    *router.urls,
    path("purchase-requests/", purchase_request, name="purchase-request"),
    path("rental-bookings/", rental_booking, name="rental-booking"),
    path("payments/stripe/webhook/", stripe_webhook, name="stripe-webhook"),
]
