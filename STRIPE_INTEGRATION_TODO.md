# Stripe integration: production status and remaining verification

Production checkout is enabled as of 2026-10-31. The live Kitaly account has charges and payouts enabled, with no outstanding verification requirements. The live restricted key and webhook signing secret are stored in the owner-only server environment file. UK-only delivery is £6.50 per order. No real payment was made during activation.

## Values to replace

Scenario A applies: the existing Checkout Session creation call is in [app/payments.py](app/payments.py). Its parameters are built by `checkout_parameters()` and saved on each order before creation. There are no placeholder `sample_only` values in that flow:

| Field | Existing value | Action |
| --- | --- | --- |
| `mode` | `payment` | Keep: shirts are one-time purchases. |
| `success_url` | Public origin + the actual order confirmation route | Keep. |
| `cancel_url` | Public origin + the actual order return route | Keep. |
| `line_items` | Saved shirt name, currency and public price; quantity 1 | Keep. Stripe Price IDs are not needed because the integration uses inline `price_data`. |

Production secrets are configured. Store them only in the ignored server `.env` at `/var/www/kitaly/kitaly/.env`:

| Variable | Required value |
| --- | --- |
| `STRIPE_SECRET_KEY` | A live key (`rk_live_` or `sk_live_`) from the business's live Stripe account. |
| `STRIPE_WEBHOOK_SECRET` | The `whsec_` signing secret belonging to that account's live webhook destination. |
| `PUBLIC_BASE_URL` | `https://kitaly-official.com` |
| `STRIPE_SHIPPING_COUNTRIES` | `GB` |
| `STRIPE_SHIPPING_RATES` | `{"GBP":650}` |
| `STRIPE_ENABLED` | `true`: enabled after live configuration and webhook verification. |

No publishable key is required for this server-side redirect integration. Do not put secret keys in browser code, Git, chat or shell command arguments. Use a hidden input prompt and restrict the server `.env` to its owner. Any key-entry helper must accept both `rk_live_` and `sk_live_` prefixes.

## Configured parameters

**File:** [app/payments.py](app/payments.py).

| Parameter | Value |
| --- | --- |
| `ui_mode` | `hosted` (installed Python SDK 14.4.2; below the supplied 21.0.0 threshold) |
| `billing_address_collection` | `auto` |
| `phone_number_collection.enabled` | `false` |
| `automatic_tax.enabled` | `false` |
| `allow_promotion_codes` | `false` |
| `submit_type` | `auto` |
| `integration_identifier` | `hosted_web_0001` |
| `origin_context` | `web` |

`payment_method_collection` is intentionally omitted because this integration uses `payment`, not `subscription`, as required by rule 8 of the supplied task. No API version override or dependency upgrade was added.

The user explicitly confirmed retaining the existing UK-only £6.50 shipping parameters and order references. Existing card-only payment methods, disabled Adaptive Pricing, locale and expiration settings are also retained to preserve the tested currency, fulfillment and reservation behavior. Removing order metadata would prevent the existing webhook from finding the order. Real prices and return URLs are unchanged.

## Setup and next steps

1. **Completed: live access and activation.** The browser login originally had the Sandbox User role in the main account. Renewed access resolved this, the owner submitted activation, and the plugin now authorizes live Kitaly (`acct_1UUqoYAVlA5pcvDe`). Stripe reports `charges_enabled=true`, `payouts_enabled=true` and no currently due requirements.
2. **Completed: live key.** The owner created the restricted Checkout Sessions key and entered it through the hidden SSH prompt. The server verified read access; a configuration-only live Checkout verified create and expire access. Retrieving that same Session through the plugin confirmed the key belongs to the intended Kitaly account.
3. **Completed: live webhook.** `we_1UWgsgAVlA5pcvDeNeey8GVa` targets `https://kitaly-official.com/stripe/webhook`, subscribing to `checkout.session.completed`, `checkout.session.expired`, `checkout.session.async_payment_succeeded` and `checkout.session.async_payment_failed`. Its API version matches the server SDK: `2026-02-25.clover`. The signing secret is saved securely on the server. Valid and invalid signature probes returned HTTP 200 and 400 respectively. Stripe's actual live expiration webhook returned HTTP 200.
4. **Completed: enabled and checked.** `payments check` reports LIVE and checkout enabled, UK-only shipping and GBP 650 minor units. The production service is active; an eligible public shirt page returns HTTP 200 and contains the Buy now form. A configuration-only £1 live Session correctly totaled £7.50, and was immediately expired without payment or any inventory reservation.
5. **Remaining: first real payment verification.** No live payment, charge or refund was made. A paid sandbox order and signed completion callback passed previously. Verify the first genuine live order, paid status and receipt delivery. Any controlled real purchase/refund requires explicit agreement on the amount and item. Manage prices and paid orders in Inventory → Orders; fulfill only confirmed paid orders. Use `venv/bin/flask --app run.py payments reconcile` to recover missed callbacks; do not manually release stock with an active Checkout Session.

### Structure and flow

Only the existing checkout parameter dictionary was changed; no routes, models, dependencies, environment loaders or webhook handlers were added. This TODO is the only new file.

Buy now → reserve the shirt and snapshot its price/delivery fee → create Stripe-hosted Checkout → collect payment/address at Stripe → signed webhook verifies the order and total → record payment and mark the shirt sold → show the existing confirmation page.

### Validation

- `venv/bin/python -m unittest test.test_payments`: 17 tests pass.
- Isolated sandbox Checkout accepted the Studio fields using Python SDK 14.4.2 and displayed a £1 test item + £6.50 UK delivery = £7.50.
- The full £7.50 sandbox payment completed; the signed webhook returned HTTP 200 and the matching disposable order was recorded as paid. Stripe retrieval confirmed the configured settings, GBP currency and UK-only destination.
- Use only sandbox keys and disposable inventory for tests. Stripe's test Visa is `4242 4242 4242 4242`, with any future expiry and any three-digit CVC. Never use test cards in live mode.
- Production payments are now enabled after live key, account ownership, amount, signature and actual expiration-webhook verification. A real paid order remains untested.

### Resources

- [Stripe Checkout Session API](https://docs.stripe.com/api/checkout/sessions/create)
- [Restricted key permissions](https://docs.stripe.com/keys/restricted-api-keys)
- [Stripe account setup](https://docs.stripe.com/get-started/account/set-up)
- [Stripe testing](https://docs.stripe.com/testing)
- [Stripe Support](https://support.stripe.com)
- [Stripe MCP](https://docs.stripe.com/mcp)

## Cart release — 2026-11-01

The catalogue cards and product pages now add to a session-backed cart. A header bag icon shows the item count on mobile and desktop. `/cart` supports review and removal; `/cart/checkout` creates one Checkout Session for all items with one £6.50 UK delivery fee. Adding to cart does not reserve stock. Checkout locks inventory in ID order and creates unique reservations for every item. Verified payment sells every reserved item; confirmed expiration releases all of them. Existing single-shirt orders are backfilled by migration `a91c4e72d810` and keep their original checkout snapshots. Admin orders and customer confirmations list each item.

Validation: 82 Python tests pass, including multi-item totals, sold/price changes, duplicate adds, stock conflicts and expiration. Chromium and mobile WebKit exercised add, remove, persisted cart and responsive controls. A two-shirt Stripe sandbox payment (£1 + £2 + £6.50 delivery = £9.50) completed with a signed completion webhook and both disposable items marked sold. No real payment was made for the cart release.
