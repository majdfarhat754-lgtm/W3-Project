from django.contrib import admin

from .models import Car, PurchaseRequest, RentalBooking


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = (
        "stock_number", "year", "make", "model", "price", "rental_daily_rate",
        "mileage", "available_for_sale", "featured",
    )
    list_filter = ("make", "fuel_type", "transmission", "featured")
    search_fields = ("stock_number", "make", "model")
    ordering = ("-created_at",)


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "car", "customer_name", "email", "status", "amount", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("customer_name", "email", "phone", "car__stock_number", "car__make")
    readonly_fields = ("amount", "checkout_session_id", "checkout_expires_at", "created_at")


@admin.register(RentalBooking)
class RentalBookingAdmin(admin.ModelAdmin):
    list_display = (
        "id", "car", "customer_name", "pickup_date", "return_date",
        "status", "total_amount", "created_at",
    )
    list_filter = ("status", "pickup_date", "created_at")
    search_fields = ("customer_name", "email", "phone", "car__stock_number", "car__make")
    readonly_fields = (
        "daily_rate", "total_amount", "checkout_session_id",
        "checkout_expires_at", "created_at",
    )
