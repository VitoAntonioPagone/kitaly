# Stripe payments for Kitaly

The integration is implemented locally. It is **not live** until the server is deployed, the matching Stripe secrets and shipping configuration are installed, and a real test Checkout succeeds.

Customers buy one shirt at its saved public price using Stripe-hosted Checkout. Cards and eligible card wallets are supported. Kitaly never receives card details. Stripe collects the buyer's email and delivery address. A verified payment marks the item sold and saves the order in **Inventory → Orders** at `<ADMIN_URL_PREFIX>/orders`.

## 1. Decide delivery settings

Set allowed delivery countries and a fixed delivery fee for each product currency you want to accept. A currency without a configured fee has no Buy now button. Fees are integer minor units: `500` means £5.00 in GBP or €5.00 in EUR; `0` explicitly enables free delivery. This first version uses the same fee for all allowed destinations, per currency, and charges delivery once per single-item order.

Confirm prices and delivery fees before enabling checkout. Automatic tax calculation, discounts, multiple-item carts and country-specific shipping fees are not implemented. Review your business's pricing/tax requirements before choosing those settings.

## 2. Configure a Stripe sandbox locally

Use your existing Stripe account's sandbox/test secret key. Keep secrets in `.env` or your hosting environment, outside Git; do not paste them in chat. Hosted Checkout does not need a publishable key or Stripe Product/Price IDs.

Copy the payment variable names from `.env.example` into your existing `.env` (do not replace the database or existing app secrets):

```dotenv
STRIPE_ENABLED=false
STRIPE_SECRET_KEY=your-test-secret-key
STRIPE_WEBHOOK_SECRET=your-local-listener-signing-secret
PUBLIC_BASE_URL=http://127.0.0.1:5001
STRIPE_SHIPPING_COUNTRIES=your-comma-separated-country-codes
STRIPE_SHIPPING_RATES={"GBP":500}
```

The £5 shipping fee above is an example, not an agreed delivery policy. Country codes use ISO alpha-2 codes, e.g. `GB,IT,CH`, and must be supported by Stripe Checkout. Existing product currencies GBP, EUR, CHF and USD are supported. Checkout requires a positive public price from 0.50 through 999,999.99 in the product currency; products without a price and sold/hidden products cannot be purchased.

Install dependencies and apply the new migration against the intended local/test database:

```bash
source venv/bin/activate
pip install -r requirements.txt
flask --app run.py db upgrade
```

Install the [Stripe CLI](https://docs.stripe.com/stripe-cli), then run in another terminal:

```bash
stripe login
stripe listen --events checkout.session.completed,checkout.session.expired,checkout.session.async_payment_succeeded,checkout.session.async_payment_failed --forward-to http://127.0.0.1:5001/stripe/webhook
```

Put the listener's `whsec_...` value in `STRIPE_WEBHOOK_SECRET`. Set `STRIPE_ENABLED=true`, restart Flask, and verify configuration:

```bash
flask --app run.py payments check
python run.py
```

Use a disposable test product with a public price, then click **Buy now**. Use Stripe's test card `4242 4242 4242 4242`, a future expiry and any CVC. Verify the success page, the sold flag and the order's customer/delivery details in the admin orders page. Also test a declined card, 3-D Secure, returning without paying, a second buyer and an expired Checkout Session. To test expiration without waiting an hour, expire that Session in Stripe or with `stripe checkout sessions expire SESSION_ID`.

The app's automated tests mock Stripe API calls and verify actual webhook signatures. They do not prove the account is activated or the production keys/webhook are working.

```bash
venv/bin/python -m unittest test.test_payments -v
```

## 3. Activate the existing account and deploy

In Stripe, complete any outstanding business verification and payout-bank requirements. Configure your business name, support details, branding and successful-payment email receipts in the Dashboard. Kitaly provides the on-site confirmation; receipt emails are sent by Stripe when enabled. Prepare your store's shipping, returns and privacy information; the existing footer information links are currently paused in the app and this integration does not publish new policy content.

Deploy the code to your VPS, install dependencies and run `flask --app run.py db upgrade` before restarting the app. Back up the production database first. The repository's `deploy.sh` follows this dependency/migration/restart sequence after code is pushed. This task does not push or deploy automatically.

Configure the server environment with:

- `PUBLIC_BASE_URL=https://kitaly-official.com` (or the exact public HTTPS origin used by customers).
- Your **live** `STRIPE_SECRET_KEY` from the same Stripe account.
- The agreed shipping countries and currency fees.
- `STRIPE_ENABLED=false` until the webhook is set up.

In [Stripe Workbench → Webhooks](https://dashboard.stripe.com/webhooks), create a **snapshot** event destination for **your account**, using the API version matching the installed Stripe SDK (`python -c "import stripe; print(stripe.api_version)"`). Register:

```text
https://kitaly-official.com/stripe/webhook
```

Subscribe to:

```text
checkout.session.completed
checkout.session.expired
checkout.session.async_payment_succeeded
checkout.session.async_payment_failed
```

Save that live endpoint's signing secret as `STRIPE_WEBHOOK_SECRET` on the server. It is different from the local CLI secret. Run `payments check`, set `STRIPE_ENABLED=true` and restart the app. Verify webhook delivery in Workbench and perform an agreed small live purchase to confirm the entire deployment, then refund it in Stripe if appropriate. No real payment has been initiated by this implementation task.

## Order handling and recovery

Only ship **PAID** orders. The orders page provides the delivery details and a Stripe payment link. Use Stripe to issue refunds and monitor disputes; those actions do not change Kitaly's sold flag automatically. Review the physical stock before any relisting. Paid and reserved items are protected from inventory edits/deletion to preserve stock and payment records. Orders requiring review stay reserved.

Sessions last one hour. Clicking Back or closing Checkout does not release a reservation. A signed expiration event or a direct retrieval from Stripe must confirm expiration first. Paid reservations stay locked, preventing accidental resale. Repeated clicks from the original browser offer **Resume checkout**. The public order page is accessible only from that browser; admin orders remain available to the owner.

A network timeout during creation can mean Stripe accepted the payment session but the app did not receive its ID. The order stays reserved and retries reuse the same idempotency key and frozen price/delivery settings. If a webhook is missed or creation stops midway, run against the matching Stripe account and mode:

```bash
flask --app run.py payments reconcile
```

For a failed creation with no Session found, after the one-hour creation window plus five minutes:

```bash
flask --app run.py payments release-uncreated ORDER_ID
```

This command searches Stripe first and reconciles any Session it finds. It only releases a failed order if no Session exists and its creation window has closed. Never clear reservations manually just because a browser returned or a local timer elapsed. Run reconciliation periodically in normal server operations to recover missed webhooks.

References: [Stripe Checkout API](https://docs.stripe.com/api/checkout/sessions/create), [webhook signature verification](https://docs.stripe.com/webhooks), [limited inventory](https://docs.stripe.com/payments/checkout/managing-limited-inventory).
