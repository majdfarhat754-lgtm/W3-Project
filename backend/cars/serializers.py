from datetime import date

from rest_framework import serializers

from .models import Car


class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = [
            "id",
            "stock_number",
            "make",
            "model",
            "year",
            "price",
            "rental_daily_rate",
            "mileage",
            "transmission",
            "fuel_type",
            "body_style",
            "exterior_color",
            "image_url",
            "description",
            "featured",
            "available_for_sale",
            "created_at",
        ]
        read_only_fields = fields


class CustomerDetailsSerializer(serializers.Serializer):
    car_id = serializers.PrimaryKeyRelatedField(
        queryset=Car.objects.all(), source="car"
    )
    customer_name = serializers.CharField(max_length=120, trim_whitespace=True)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=30, trim_whitespace=True)
    checkout = serializers.BooleanField(default=False, write_only=True)


class PurchaseRequestSerializer(CustomerDetailsSerializer):
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)

    def validate_customer_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Enter your name.")
        return value

    def validate_phone(self, value):
        if not value.strip():
            raise serializers.ValidationError("Enter a phone number.")
        return value


class RentalBookingSerializer(CustomerDetailsSerializer):
    pickup_date = serializers.DateField()
    return_date = serializers.DateField()

    def validate_customer_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Enter your name.")
        return value

    def validate_phone(self, value):
        if not value.strip():
            raise serializers.ValidationError("Enter a phone number.")
        return value

    def validate_pickup_date(self, value):
        if value < date.today():
            raise serializers.ValidationError("Pickup date cannot be in the past.")
        return value

    def validate(self, attrs):
        if attrs["return_date"] <= attrs["pickup_date"]:
            raise serializers.ValidationError(
                {"return_date": "Return date must be after the pickup date."}
            )
        return attrs
