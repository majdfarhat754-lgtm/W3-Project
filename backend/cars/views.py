import logging
from datetime import timedelta
from decimal import Decimal

import stripe
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .models import Car, ProcessedStripeEvent, PurchaseRequest, RentalBooking
from .serializers import CarSerializer, PurchaseRequestSerializer, RentalBookingSerializer

logger = logging.getLogger(__name__)

CHECKOUT_MINUTES = 35


def _checkout_is_configured():
    return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_WEBHOOK_SECRET)


def _amount_in_cents(amount):
    return int(Decimal(amount) * 100)


def _create_checkout_session(*, record_type, record_id, amount, email, description, success_kind):
    expires_at = timezone.now() + timedelta(minutes=CHECKOUT_MINUTES)
    session = stripe.checkout.Session.create(
        api_key=settings.STRIPE_SECRET_KEY,
        mode="payment",
        payment_method_types=["card"],
        customer_email=email,
        line_items=[
            {
                "price_data": {
                    "currency": settings.STRIPE_CURRENCY,
                    "unit_amount": _amount_in_cents(amount),
                    "product_data": {"name": description},
                },
                "quantity": 1,
            }
        ],
        metadata={"record_type": record_type, "record_id": str(record_id)},
        success_url=f"{settings.FRONTEND_URL}/?checkout=success&kind={success_kind}",
        cancel_url=f"{settings.FRONTEND_URL}/?checkout=cancel&kind={success_kind}",
        expires_at=int(expires_at.timestamp()),
    )
    return session, expires_at


class CarViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CarSerializer

    def get_queryset(self):
        queryset = Car.objects.filter(available_for_sale=True)
        search = self.request.query_params.get("q", "").strip()
        make = self.request.query_params.get("make", "").strip()
        fuel_type = self.request.query_params.get("fuel_type", "").strip()

        if search:
            queryset = queryset.filter(
                Q(make__icontains=search)
                | Q(model__icontains=search)
                | Q(description__icontains=search)
                | Q(stock_number__icontains=search)
            )
        if make:
            queryset = queryset.filter(make__iexact=make)
        if fuel_type:
            queryset = queryset.filter(fuel_type__iexact=fuel_type)

        return queryset


@api_view(["POST"])
@throttle_classes([ScopedRateThrottle])
def purchase_request(request):
    serializer = PurchaseRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    car_id = data.pop("car").pk
    checkout = data.pop("checkout")
    if checkout and not _checkout_is_configured():
        return Response(
            {"detail": "Online checkout is not configured. Please send a purchase request instead."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    with transaction.atomic():
        car = Car.objects.select_for_update().get(pk=car_id)
        if not car.available_for_sale:
            return Response(
                {"detail": "This vehicle is no longer available for purchase."},
                status=status.HTTP_409_CONFLICT,
            )

        if not checkout:
            purchase = PurchaseRequest.objects.create(car=car, amount=car.price, **data)
            return Response(
                {"id": purchase.id, "status": purchase.status},
                status=status.HTTP_201_CREATED,
            )

        now = timezone.now()
        if PurchaseRequest.objects.filter(
            car=car,
            status=PurchaseRequest.Status.PENDING_PAYMENT,
            checkout_expires_at__gt=now,
        ).exists():
            return Response(
                {"detail": "Someone is already checking out this vehicle. Please try again shortly."},
                status=status.HTTP_409_CONFLICT,
            )

        purchase = PurchaseRequest.objects.create(
            car=car,
            amount=car.price,
            status=PurchaseRequest.Status.PENDING_PAYMENT,
            **data,
        )
        try:
            session, expires_at = _create_checkout_session(
                record_type="purchase",
                record_id=purchase.id,
                amount=purchase.amount,
                email=purchase.email,
                description=f"{car.year} {car.make} {car.model} — advertised price",
                success_kind="purchase",
            )
        except stripe.error.StripeError:
            logger.exception("Stripe checkout session creation failed for purchase %s", purchase.id)
            purchase.delete()
            return Response(
                {"detail": "Secure checkout is temporarily unavailable. Please try again or send a request."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        purchase.checkout_session_id = session.id
        purchase.checkout_expires_at = expires_at
        purchase.save(update_fields=["checkout_session_id", "checkout_expires_at"])

    return Response(
        {"id": purchase.id, "status": purchase.status, "checkout_url": session.url},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@throttle_classes([ScopedRateThrottle])
def rental_booking(request):
    serializer = RentalBookingSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    car_id = data.pop("car").pk
    checkout = data.pop("checkout")
    if checkout and not _checkout_is_configured():
        return Response(
            {"detail": "Online checkout is not configured. Please send a rental request instead."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    with transaction.atomic():
        car = Car.objects.select_for_update().get(pk=car_id)
        days = (data["return_date"] - data["pickup_date"]).days
        daily_rate = car.rental_daily_rate
        if checkout and daily_rate <= 0:
            return Response(
                {"detail": "Online rental is not available for this vehicle. Please send a request."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        overlaps = RentalBooking.objects.filter(
            car=car,
            pickup_date__lt=data["return_date"],
            return_date__gt=data["pickup_date"],
        ).filter(
            Q(status=RentalBooking.Status.CONFIRMED)
            | Q(status=RentalBooking.Status.PAYMENT_REVIEW)
            | Q(
                status=RentalBooking.Status.PENDING_PAYMENT,
                checkout_expires_at__gt=now,
            )
        )
        if overlaps.exists():
            return Response(
                {"detail": "This vehicle is unavailable for those dates. Please choose other dates."},
                status=status.HTTP_409_CONFLICT,
            )

        total_amount = (daily_rate * days).quantize(Decimal("0.01"))
        if not checkout:
            booking = RentalBooking.objects.create(
                car=car,
                daily_rate=daily_rate,
                total_amount=total_amount,
                **data,
            )
            return Response(
                {
                    "id": booking.id,
                    "status": booking.status,
                    "total_amount": str(booking.total_amount),
                    "days": days,
                },
                status=status.HTTP_201_CREATED,
            )

        booking = RentalBooking.objects.create(
            car=car,
            daily_rate=daily_rate,
            total_amount=total_amount,
            status=RentalBooking.Status.PENDING_PAYMENT,
            **data,
        )
        try:
            session, expires_at = _create_checkout_session(
                record_type="rental",
                record_id=booking.id,
                amount=booking.total_amount,
                email=booking.email,
                description=f"{car.year} {car.make} {car.model} rental — {days} days",
                success_kind="rental",
            )
        except stripe.error.StripeError:
            logger.exception("Stripe checkout session creation failed for rental %s", booking.id)
            booking.delete()
            return Response(
                {"detail": "Secure checkout is temporarily unavailable. Please try again or send a request."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        booking.checkout_session_id = session.id
        booking.checkout_expires_at = expires_at
        booking.save(update_fields=["checkout_session_id", "checkout_expires_at"])

    return Response(
        {
            "id": booking.id,
            "status": booking.status,
            "total_amount": str(booking.total_amount),
            "days": days,
            "checkout_url": session.url,
        },
        status=status.HTTP_201_CREATED,
    )


def _handle_checkout_event(event):
    event_type = event["type"]
    session = event["data"]["object"]
    metadata = session.get("metadata") or {}
    record_type = metadata.get("record_type")
    record_id = metadata.get("record_id")

    if record_type == "purchase":
        record_model = PurchaseRequest
        pending_status = PurchaseRequest.Status.PENDING_PAYMENT
        retry_status = PurchaseRequest.Status.NEW
    elif record_type == "rental":
        record_model = RentalBooking
        pending_status = RentalBooking.Status.PENDING_PAYMENT
        retry_status = RentalBooking.Status.REQUESTED
    else:
        return

    try:
        record = record_model.objects.select_for_update().get(
            pk=record_id,
            checkout_session_id=session["id"],
        )
    except (record_model.DoesNotExist, TypeError, ValueError):
        logger.warning("Stripe event references an unknown %s record", record_type)
        return

    if event_type == "checkout.session.expired":
        if record.status == pending_status:
            record.status = retry_status
            record.save(update_fields=["status"])
        return

    if event_type not in {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    } or session.get("payment_status") != "paid":
        return

    expected_amount = (
        record.amount if record_type == "purchase" else record.total_amount
    )
    if session.get("amount_total") != _amount_in_cents(expected_amount):
        record.status = (
            PurchaseRequest.Status.PAYMENT_REVIEW
            if record_type == "purchase"
            else RentalBooking.Status.PAYMENT_REVIEW
        )
        record.payment_received_at = timezone.now()
        record.save(update_fields=["status", "payment_received_at"])
        if record_type == "purchase":
            car = Car.objects.select_for_update().get(pk=record.car_id)
            if car.available_for_sale:
                car.available_for_sale = False
                car.save(update_fields=["available_for_sale"])
        logger.error("Stripe payment amount mismatch for %s %s", record_type, record.pk)
        return

    if record_type == "purchase":
        car = Car.objects.select_for_update().get(pk=record.car_id)
        if car.available_for_sale:
            car.available_for_sale = False
            car.save(update_fields=["available_for_sale"])
            record.status = PurchaseRequest.Status.PAID
        else:
            record.status = PurchaseRequest.Status.PAYMENT_REVIEW
            logger.error("Paid purchase %s requires review because the car is unavailable", record.pk)
        record.payment_received_at = timezone.now()
        record.save(update_fields=["status", "payment_received_at"])
        return

    car = Car.objects.select_for_update().get(pk=record.car_id)
    overlap = RentalBooking.objects.filter(
        car=car,
        pickup_date__lt=record.return_date,
        return_date__gt=record.pickup_date,
    ).exclude(pk=record.pk).filter(
        Q(status=RentalBooking.Status.CONFIRMED)
        | Q(status=RentalBooking.Status.PAYMENT_REVIEW)
        | Q(
            status=RentalBooking.Status.PENDING_PAYMENT,
            checkout_expires_at__gt=timezone.now(),
        )
    ).exists()
    if overlap:
        record.status = RentalBooking.Status.PAYMENT_REVIEW
        logger.error("Paid rental %s requires review because dates overlap", record.pk)
    else:
        record.status = RentalBooking.Status.CONFIRMED
    record.payment_received_at = timezone.now()
    record.save(update_fields=["status", "payment_received_at"])


@csrf_exempt
@api_view(["POST"])
def stripe_webhook(request):
    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse("Stripe webhook is not configured.", status=503)

    try:
        event = stripe.Webhook.construct_event(
            request.body,
            request.headers.get("Stripe-Signature", ""),
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse("Invalid Stripe webhook signature or payload.", status=400)

    try:
        with transaction.atomic():
            _, created = ProcessedStripeEvent.objects.get_or_create(
                event_id=event["id"],
                defaults={"event_type": event["type"]},
            )
            if created:
                _handle_checkout_event(event)
    except stripe.error.StripeError:
        logger.exception("Stripe webhook processing failed for event %s", event["id"])
        return HttpResponse("Webhook processing failed.", status=500)

    return HttpResponse(status=200)


purchase_request.cls.throttle_scope = "purchase_request"
rental_booking.cls.throttle_scope = "rental_booking"
