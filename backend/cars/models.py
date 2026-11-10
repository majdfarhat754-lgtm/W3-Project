from django.core.validators import MinValueValidator
from django.db import models


class Car(models.Model):
    class Transmission(models.TextChoices):
        AUTOMATIC = "Automatic", "Automatic"
        MANUAL = "Manual", "Manual"

    class FuelType(models.TextChoices):
        GASOLINE = "Gasoline", "Gasoline"
        DIESEL = "Diesel", "Diesel"
        HYBRID = "Hybrid", "Hybrid"
        ELECTRIC = "Electric", "Electric"

    stock_number = models.CharField(max_length=20, unique=True)
    make = models.CharField(max_length=80, db_index=True)
    model = models.CharField(max_length=100)
    year = models.PositiveSmallIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    rental_daily_rate = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    mileage = models.PositiveIntegerField()
    transmission = models.CharField(max_length=20, choices=Transmission.choices)
    fuel_type = models.CharField(max_length=20, choices=FuelType.choices)
    body_style = models.CharField(max_length=40, blank=True)
    exterior_color = models.CharField(max_length=40, blank=True)
    image_url = models.URLField(max_length=500)
    description = models.TextField(blank=True)
    featured = models.BooleanField(default=False)
    available_for_sale = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-featured", "-year", "price"]

    def __str__(self):
        return f"{self.year} {self.make} {self.model}"


class PurchaseRequest(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New request"
        PENDING_PAYMENT = "pending_payment", "Awaiting payment"
        PAID = "paid", "Payment received"
        PAYMENT_REVIEW = "payment_review", "Payment needs review"
        CLOSED = "closed", "Closed"

    car = models.ForeignKey(Car, on_delete=models.PROTECT, related_name="purchase_requests")
    customer_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    notes = models.CharField(max_length=1000, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    checkout_session_id = models.CharField(max_length=255, blank=True, db_index=True)
    checkout_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    payment_received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Purchase request #{self.pk} — {self.car}"


class RentalBooking(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Request received"
        PENDING_PAYMENT = "pending_payment", "Awaiting payment"
        CONFIRMED = "confirmed", "Confirmed"
        PAYMENT_REVIEW = "payment_review", "Payment needs review"
        CANCELLED = "cancelled", "Cancelled"

    car = models.ForeignKey(Car, on_delete=models.PROTECT, related_name="rental_bookings")
    customer_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    pickup_date = models.DateField()
    return_date = models.DateField()
    daily_rate = models.DecimalField(max_digits=8, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    checkout_session_id = models.CharField(max_length=255, blank=True, db_index=True)
    checkout_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    payment_received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["car", "pickup_date", "return_date", "status"]),
        ]

    def __str__(self):
        return f"Rental #{self.pk} — {self.car} ({self.pickup_date} to {self.return_date})"


class ProcessedStripeEvent(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    received_at = models.DateTimeField(auto_now_add=True)
