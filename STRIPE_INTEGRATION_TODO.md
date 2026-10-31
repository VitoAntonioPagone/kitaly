# Stripe integration: remaining setup

## Values to replace

Scenario A applies: the existing Checkout Session creation call is in [app/payments.py](app/payments.py). Its parameters are built by `checkout_parameters()` and saved on each order before creation. There are no placeholder `sample_only` values in that flow:

| Field | Existing value | Action |
| --- | --- | --- |
| `mode` | `payment` | Keep: shirts are one-time purchases. |
| `success_url` | Public origin + the actual order confirmation route | Keep. |
| `cancel_url` | Public origin + the actual order return route | Keep. |
| `line_items` | Saved shirt name, currency and public price; quantity 1 | Keep. Stripe Price IDs are not needed because the integration uses inline `price_data`. |

Production secrets are still missing, rather than placeholder values in the checkout code. Store these only in the ignored server `.env` at `/var/www/kitaly/kitaly/.env`:

| Variable | Required value |
| --- | --- |
| `STRIPE_SECRET_KEY` | A live key (`rk_live_` or `sk_live_`) from the business's live Stripe account. |
| `STRIPE_WEBHOOK_SECRET` | The `whsec_` signing secret belonging to that account's live webhook destination. |
| `PUBLIC_BASE_URL` | `https://kitaly-official.com` |
| `STRIPE_SHIPPING_COUNTRIES` | `GB` |
| `STRIPE_SHIPPING_RATES` | `{"GBP":650}` |
| `STRIPE_ENABLED` | Keep `false` until live credentials and the webhook have been verified. |

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

1. **Resolve live Stripe account access.** In Chrome, leaving the sandbox showed the main Kitaly account, but both “Activate products” and Stripe's documented business-onboarding URL redirected to Sandboxes. This is an observed account/session blocker; its underlying cause is not confirmed. Sign back in as the owner and retry [business verification](https://dashboard.stripe.com/account/onboarding). If the redirect persists, contact Stripe Support. Do not create a duplicate account as a workaround. The owner must provide accurate business/identity/bank details and review any terms Stripe requires.
2. **Create and securely save a live integration key.** The current app calls Checkout Sessions create, retrieve and list. Start with Checkout Sessions write access (which includes read), then verify the key's access using Stripe's request logs. Follow any additional permission requirements returned by Stripe. Do not grant full account access solely to bypass permission errors.
3. **Create a live snapshot webhook destination** for your account at `https://kitaly-official.com/stripe/webhook`, subscribing to `checkout.session.completed`, `checkout.session.expired`, `checkout.session.async_payment_succeeded` and `checkout.session.async_payment_failed`. Check the server SDK's API version with `venv/bin/python -c 'import stripe; print(stripe.api_version)'`; use the matching destination version. Save its signing secret as `STRIPE_WEBHOOK_SECRET`.
4. **Validate before enabling.** From the server project directory, run `venv/bin/flask --app run.py payments check`. Review Stripe account readiness, receipt settings and delivery/returns information. Once these checks succeed, set `STRIPE_ENABLED=true` and restart `kitaly`. Verify live webhook delivery. A real purchase/refund requires the owner's explicit agreement on the amount and item; sandbox success alone does not prove live readiness.
5. **Operate orders.** Manage shirt prices in the existing inventory. Successful signed payments mark the reserved shirt sold and record the order under Inventory → Orders. Fulfill only confirmed paid orders. Use `venv/bin/flask --app run.py payments reconcile` to recover missed callbacks; do not manually release stock with an active Checkout Session.

### Structure and flow

Only the existing checkout parameter dictionary was changed; no routes, models, dependencies, environment loaders or webhook handlers were added. This TODO is the only new file.

Buy now → reserve the shirt and snapshot its price/delivery fee → create Stripe-hosted Checkout → collect payment/address at Stripe → signed webhook verifies the order and total → record payment and mark the shirt sold → show the existing confirmation page.

### Validation

- `venv/bin/python -m unittest test.test_payments`: 17 tests pass.
- Isolated sandbox Checkout accepted the Studio fields using Python SDK 14.4.2 and displayed a £1 test item + £6.50 UK delivery = £7.50.
- The full £7.50 sandbox payment completed; the signed webhook returned HTTP 200 and the matching disposable order was recorded as paid. Stripe retrieval confirmed the configured settings, GBP currency and UK-only destination.
- Use only sandbox keys and disposable inventory for tests. Stripe's test Visa is `4242 4242 4242 4242`, with any future expiry and any three-digit CVC. Never use test cards in live mode.
- Production payments remain disabled; no live key or webhook signing secret was configured when checked for this task.

### Resources

- [Stripe Checkout Session API](https://docs.stripe.com/api/checkout/sessions/create)
- [Restricted key permissions](https://docs.stripe.com/keys/restricted-api-keys)
- [Stripe account setup](https://docs.stripe.com/get-started/account/set-up)
- [Stripe testing](https://docs.stripe.com/testing)
- [Stripe Support](https://support.stripe.com)
- [Stripe MCP](https://docs.stripe.com/mcp)
