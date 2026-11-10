# Northline Motors

A dealership MVP with a React + Vite frontend and a Django REST Framework backend. Customers can browse cars, send purchase or rental requests, or use Stripe-hosted checkout. Staff manage cars and follow up on requests in Django admin.

## Run locally on Windows

Requirements: Node.js 20.19+ (or 22.12+) and Python 3.10+.

In the project root:

```powershell
npm install
npm run dev
```

In a second terminal:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py manage.py migrate
py manage.py seed_inventory
py manage.py createsuperuser
py manage.py runserver
```

Open the Vite URL printed in the first terminal. Vite proxies `/api` requests to Django at `http://127.0.0.1:8000`. Open `http://127.0.0.1:8000/admin/` to manage inventory and customer requests.

The sample inventory and rental rates are placeholders. Update them in the Django admin before accepting customers.

## Purchase and rental flows

- **Purchase request:** saves the customer's contact details for dealership follow-up.
- **Purchase checkout:** charges the full advertised price using Stripe Checkout. Taxes, title, registration, and other fees are not calculated or included. Payment is not a signed purchase contract.
- **Rental request:** saves the requested dates; it does not reserve the car until the dealership confirms.
- **Rental checkout:** charges the configured daily rate times the number of days between pickup and return. A booking is confirmed after Stripe's signed payment webhook arrives. Rental deposits, taxes, insurance, mileage limits, late fees, and other terms are not included.
- **Paperwork:** the site provides a general document checklist only. It does not collect document uploads, generate/sign legal agreements, or replace local legal requirements. The country/jurisdiction was not provided, so the checklist is not jurisdiction-specific.

Only collect the contact information needed to follow up. Do not request card or driver-license numbers in messages. Card details go directly to Stripe's hosted checkout and are not stored by this app.

## Enable Stripe test checkout

1. Create a Stripe account and use **test-mode** API keys.
2. In a third terminal, forward Stripe events to the local webhook:

   ```powershell
   stripe listen --forward-to localhost:8000/api/payments/stripe/webhook/
   ```

3. Copy the `whsec_...` secret printed by Stripe CLI. Set both secrets in the terminal where Django will run, then start/restart Django:

   ```powershell
   $env:STRIPE_SECRET_KEY = "sk_test_your_key"
   $env:STRIPE_WEBHOOK_SECRET = "whsec_your_webhook_secret"
   $env:STRIPE_CURRENCY = "usd"
   $env:FRONTEND_URL = "http://localhost:5173"
   py manage.py runserver
   ```

The default display currency is USD. If changing currency, use a Stripe-supported, two-decimal currency and set `STRIPE_CURRENCY` in the backend and `VITE_CURRENCY` before starting Vite. Never expose secret keys in frontend code or commit them.

Without both Stripe secrets, request submission remains available and online checkout is disabled. A successful browser redirect alone does not confirm payment; the signed webhook updates the payment and vehicle/booking status.

## API

- `GET /api/cars/` and `GET /api/cars/{id}/` — available inventory
- `POST /api/purchase-requests/` — submit a purchase request; `checkout: true` starts Stripe Checkout
- `POST /api/rental-bookings/` — request rental dates; `checkout: true` starts a paid booking
- `POST /api/payments/stripe/webhook/` — Stripe payment confirmation endpoint
- Optional inventory filters: `?q=porsche`, `?make=Audi`, `?fuel_type=Electric`

The sample data command is safe to rerun. It creates or updates the included sample cars without removing other inventory.

## Checks

```powershell
npm run build
py backend\manage.py test cars
```

## Before production

Set a strong `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, and `DJANGO_ALLOWED_HOSTS`; use live Stripe keys only after testing; configure a production database (PostgreSQL is recommended for concurrent rental availability), HTTPS, backups, privacy/terms pages, taxes, and jurisdiction-reviewed sales/rental contracts. Add customer authentication and an operational email-notification workflow if required. The included SQLite database and example inventory are for development.
