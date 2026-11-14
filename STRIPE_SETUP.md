# Stripe payments for Kitaly

The integration is implemented locally. It is **not live** until the server is deployed, the matching Stripe secrets and shipping configuration are installed, and a real test Checkout succeeds.

Customers add shirts to their cart and pay once at their saved public prices using Stripe-hosted Checkout. Cards and eligible card wallets are supported. Kitaly never receives card details. Stripe collects the buyer's email and delivery address. A verified payment marks the item sold and saves the order in **Inventory → Orders** at `<ADMIN_URL_PREFIX>/orders`.

## Sandbox verification — 2026-10-31

A Stripe sandbox secret key was supplied through a masked local prompt, verified against Stripe and saved outside the repository in `~/.config/kitaly/stripe-sandbox.env` (owner-only permissions). No key was included in chat, source code or logs. The publishable key is not required for this server-side hosted Checkout integration.

An isolated SQLite test inventory and a loopback-only test server were used. A disposable £1.00 item completed hosted Checkout using Stripe’s published test Visa. The signed `checkout.session.completed` webhook returned HTTP 200, the order was recorded as paid, and only the disposable test item was marked sold. A separate expiration test received a signed `checkout.session.expired` event and released the test reservation. Stripe confirmed `livemode=false`.

The test exposed automatic currency conversion to CHF. Checkout now explicitly disables Adaptive Pricing so the charged currency and amount match the saved GBP order. The payment regression tests include this setting.

The temporary test delivery fee was £0.00 to a UK test address; it is not the live shipping policy. That initial test left production payments and real stock unchanged. Live credentials and webhook configuration remain pending. A non-secret verification report is saved in `~/.config/kitaly/stripe-sandbox-test-report.json`.

## Royal Mail delivery settings

The current Royal Mail tariff is charged in GBP: £4.50 below £75 and free from £75 in the UK. International quotes use the configured destination and the sum of item weights plus the packaging allowance. Select the destination in the cart; Stripe Checkout accepts addresses in that country only. The previous £6.50 flat rate is available only with `ROYAL_MAIL_CHECKOUT=false` for deployments that need the legacy behavior.

Keep `STRIPE_SHIPPING_COUNTRIES=GB` until international destinations and fulfilment are ready. Enter each item’s weight contribution in admin and set `SHIPPING_PACKAGING_GRAMS` to the standard shipment packaging weight, or to `0` if item weights already include their full share of packaging. Baskets without confirmed weights require an enquiry. Enable individual countries only after checking carrier restrictions, parcel limits and import obligations. Use Delivered Duty Unpaid / DAP for destinations that allow the recipient to pay locally; otherwise arrange a duty-paid quote before taking payment. [Royal Mail’s Europe guidance](https://www.royalmail.com/europeantradeinsights) explains which services and changes to check. For US orders, Royal Mail International Tracked uses Postal Delivered Duties Paid. Agree the prepaid duty and collect it from the customer separately before dispatch; the automatic checkout excludes the US and Puerto Rico. See [Royal Mail’s US business guidance](https://www.royalmail.com/usabusinessupdates?check_logged_in=1) and the [European Commission’s guidance on low-value imports](https://taxation-customs.ec.europa.eu/news/guidance-and-legal-text-temporary-flat-fee-low-value-imports-which-will-apply-until-1-july-2028-2026-06-08_en).

## 1. Decide delivery settings

Select the allowed destinations. With the Royal Mail tariff enabled, delivery is charged once per order in GBP. For legacy flat-rate deployments only, configure `STRIPE_SHIPPING_RATES` with a fee in minor units for each checkout currency.

Confirm prices and delivery fees before enabling checkout. Automatic tax calculation and discount codes are disabled. Review your business's pricing/tax requirements before choosing those settings.

## 2. Configure a Stripe sandbox locally

Use your existing Stripe account's sandbox/test secret key. Keep secrets in `.env` or your hosting environment, outside Git; do not paste them in chat. Hosted Checkout does not need a publishable key or Stripe Product/Price IDs.

Copy the payment variable names from `.env.example` into your existing `.env` (do not replace the database or existing app secrets):

```dotenv
STRIPE_ENABLED=false
STRIPE_SECRET_KEY=your-test-secret-key
STRIPE_WEBHOOK_SECRET=your-local-listener-signing-secret
PUBLIC_BASE_URL=http://127.0.0.1:5001
STRIPE_SHIPPING_COUNTRIES=GB
ROYAL_MAIL_CHECKOUT=true
```

The settings above enable the £4.50 UK fee with free delivery from £75. Country codes use ISO alpha-2 codes, e.g. `GB,IT,CH`, and must be supported by Stripe Checkout. The Royal Mail tariff and checkout are in GBP. Non-GBP listings remain available by enquiry. Checkout requires a positive public price from 0.50 through 999,999.99 in the product currency; products without a price and sold/hidden products cannot be purchased.

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

In Stripe, complete any outstanding business verification and payout-bank requirements. Configure your business name, support details, branding and successful-payment email receipts in the Dashboard. Kitaly provides the on-site confirmation; receipt emails are sent by Stripe when enabled. Prepare your store's shipping, returns and privacy information; the storefront links to the published delivery information.

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
