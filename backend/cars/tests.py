from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import stripe
from django.test import override_settings
from rest_framework.test import APITestCase

from .models import Car, ProcessedStripeEvent, PurchaseRequest, RentalBooking


class CarApiTests(APITestCase):
    def setUp(self):
        Car.objects.create(
            stock_number="TEST-001",
            make="Audi",
            model="A4",
            year=2023,
            price="32000.00",
            rental_daily_rate="100.00",
            mileage=12000,
            transmission=Car.Transmission.AUTOMATIC,
            fuel_type=Car.FuelType.GASOLINE,
            image_url="https://example.com/a4.jpg",
        )
        Car.objects.create(
            stock_number="TEST-002",
            make="BMW",
            model="i4",
            year=2024,
            price="54000.00",
            rental_daily_rate="125.00",
            mileage=4000,
            transmission=Car.Transmission.AUTOMATIC,
            fuel_type=Car.FuelType.ELECTRIC,
            image_url="https://example.com/i4.jpg",
        )

    def test_list_returns_inventory(self):
        response = self.client.get("/api/cars/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_list_filters_by_make_and_search(self):
        response = self.client.get("/api/cars/?make=audi&q=A4")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["stock_number"], "TEST-001")

    def test_detail_returns_a_car(self):
        car = Car.objects.get(stock_number="TEST-001")

        response = self.client.get(f"/api/cars/{car.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["make"], "Audi")

    def test_purchase_request_is_saved_for_dealer_follow_up(self):
        response = self.client.post(
            "/api/purchase-requests/",
            {
                "car_id": Car.objects.get(stock_number="TEST-001").id,
                "customer_name": "Alex Customer",
                "email": "alex@example.com",
                "phone": "555-0100",
                "notes": "Please contact me.",
                "checkout": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        purchase = PurchaseRequest.objects.get(pk=response.data["id"])
        self.assertEqual(purchase.status, PurchaseRequest.Status.NEW)
        self.assertEqual(str(purchase.amount), "32000.00")

    def test_purchase_checkout_creates_stripe_session_at_advertised_price(self):
        car = Car.objects.get(stock_number="TEST-001")
        with override_settings(
            STRIPE_SECRET_KEY="sk_test_example",
            STRIPE_WEBHOOK_SECRET="whsec_example",
        ), patch(
            "cars.views.stripe.checkout.Session.create",
            return_value=SimpleNamespace(id="cs_test_purchase", url="https://checkout.example"),
        ) as create_session:
            response = self.client.post(
                "/api/purchase-requests/",
                {
                    "car_id": car.id,
                    "customer_name": "Alex Customer",
                    "email": "alex@example.com",
                    "phone": "555-0100",
                    "checkout": True,
                },
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["checkout_url"], "https://checkout.example")
        self.assertEqual(
            create_session.call_args.kwargs["line_items"][0]["price_data"]["unit_amount"],
            3200000,
        )
        self.assertEqual(
            PurchaseRequest.objects.get(pk=response.data["id"]).status,
            PurchaseRequest.Status.PENDING_PAYMENT,
        )

    def test_checkout_is_disabled_without_both_stripe_secrets(self):
        response = self.client.post(
            "/api/purchase-requests/",
            {
                "car_id": Car.objects.get(stock_number="TEST-001").id,
                "customer_name": "Alex Customer",
                "email": "alex@example.com",
                "phone": "555-0100",
                "checkout": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(PurchaseRequest.objects.count(), 0)

    def test_rental_request_calculates_total_for_each_day(self):
        pickup = date.today() + timedelta(days=2)
        response = self.client.post(
            "/api/rental-bookings/",
            {
                "car_id": Car.objects.get(stock_number="TEST-001").id,
                "customer_name": "Alex Customer",
                "email": "alex@example.com",
                "phone": "555-0100",
                "pickup_date": pickup.isoformat(),
                "return_date": (pickup + timedelta(days=3)).isoformat(),
                "checkout": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["days"], 3)
        self.assertEqual(response.data["total_amount"], "300.00")
        self.assertEqual(RentalBooking.objects.get(pk=response.data["id"]).status, "requested")

    def test_rental_checkout_uses_configured_daily_rate(self):
        car = Car.objects.get(stock_number="TEST-001")
        pickup = date.today() + timedelta(days=2)
        with override_settings(
            STRIPE_SECRET_KEY="sk_test_example",
            STRIPE_WEBHOOK_SECRET="whsec_example",
        ), patch(
            "cars.views.stripe.checkout.Session.create",
            return_value=SimpleNamespace(id="cs_test_rental", url="https://checkout.example"),
        ) as create_session:
            response = self.client.post(
                "/api/rental-bookings/",
                {
                    "car_id": car.id,
                    "customer_name": "Alex Customer",
                    "email": "alex@example.com",
                    "phone": "555-0100",
                    "pickup_date": pickup.isoformat(),
                    "return_date": (pickup + timedelta(days=3)).isoformat(),
                    "checkout": True,
                },
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["total_amount"], "300.00")
        self.assertEqual(
            create_session.call_args.kwargs["line_items"][0]["price_data"]["unit_amount"],
            30000,
        )
        self.assertEqual(
            RentalBooking.objects.get(pk=response.data["id"]).status,
            RentalBooking.Status.PENDING_PAYMENT,
        )

    def test_rental_booking_rejects_overlapping_confirmed_dates(self):
        car = Car.objects.get(stock_number="TEST-001")
        pickup = date.today() + timedelta(days=4)
        RentalBooking.objects.create(
            car=car,
            customer_name="Existing Customer",
            email="existing@example.com",
            phone="555-0111",
            pickup_date=pickup,
            return_date=pickup + timedelta(days=3),
            daily_rate=car.rental_daily_rate,
            total_amount="300.00",
            status=RentalBooking.Status.CONFIRMED,
        )

        response = self.client.post(
            "/api/rental-bookings/",
            {
                "car_id": car.id,
                "customer_name": "Alex Customer",
                "email": "alex@example.com",
                "phone": "555-0100",
                "pickup_date": (pickup + timedelta(days=1)).isoformat(),
                "return_date": (pickup + timedelta(days=4)).isoformat(),
                "checkout": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(RentalBooking.objects.count(), 1)

    def test_rental_rejects_return_date_before_pickup(self):
        pickup = date.today() + timedelta(days=3)
        response = self.client.post(
            "/api/rental-bookings/",
            {
                "car_id": Car.objects.get(stock_number="TEST-001").id,
                "customer_name": "Alex Customer",
                "email": "alex@example.com",
                "phone": "555-0100",
                "pickup_date": pickup.isoformat(),
                "return_date": pickup.isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("return_date", response.data)

    def test_signed_webhook_confirms_purchase_and_is_idempotent(self):
        car = Car.objects.get(stock_number="TEST-001")
        purchase = PurchaseRequest.objects.create(
            car=car,
            customer_name="Alex Customer",
            email="alex@example.com",
            phone="555-0100",
            amount=car.price,
            status=PurchaseRequest.Status.PENDING_PAYMENT,
            checkout_session_id="cs_paid_purchase",
        )
        event = {
            "id": "evt_paid_purchase",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_paid_purchase",
                    "metadata": {"record_type": "purchase", "record_id": str(purchase.id)},
                    "payment_status": "paid",
                    "amount_total": 3200000,
                }
            },
        }

        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test"), patch(
            "cars.views.stripe.Webhook.construct_event", return_value=event
        ):
            response = self.client.post(
                "/api/payments/stripe/webhook/",
                data=b"{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="signature",
            )
            duplicate_response = self.client.post(
                "/api/payments/stripe/webhook/",
                data=b"{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="signature",
            )

        purchase.refresh_from_db()
        car.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(duplicate_response.status_code, 200)
        self.assertEqual(purchase.status, PurchaseRequest.Status.PAID)
        self.assertFalse(car.available_for_sale)
        self.assertEqual(ProcessedStripeEvent.objects.count(), 1)

    def test_signed_webhook_confirms_paid_rental(self):
        car = Car.objects.get(stock_number="TEST-001")
        pickup = date.today() + timedelta(days=5)
        booking = RentalBooking.objects.create(
            car=car,
            customer_name="Alex Customer",
            email="alex@example.com",
            phone="555-0100",
            pickup_date=pickup,
            return_date=pickup + timedelta(days=2),
            daily_rate=car.rental_daily_rate,
            total_amount="200.00",
            status=RentalBooking.Status.PENDING_PAYMENT,
            checkout_session_id="cs_paid_rental",
            checkout_expires_at=None,
        )
        event = {
            "id": "evt_paid_rental",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_paid_rental",
                    "metadata": {"record_type": "rental", "record_id": str(booking.id)},
                    "payment_status": "paid",
                    "amount_total": 20000,
                }
            },
        }

        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test"), patch(
            "cars.views.stripe.Webhook.construct_event", return_value=event
        ):
            response = self.client.post(
                "/api/payments/stripe/webhook/",
                data=b"{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="signature",
            )

        booking.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(booking.status, RentalBooking.Status.CONFIRMED)
