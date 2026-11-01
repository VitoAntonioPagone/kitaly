# Orders, sold inventory and dispatch emails

## Daily workflow

1. A verified paid Stripe Checkout automatically marks every purchased shirt sold. No action is required in the dashboard. Available inventory excludes sold shirts; Sold inventory includes them. An unpaid or cancelled checkout never marks a shirt sold. Expiration releases its reservations.
2. Open **Inventory → Sold → Online purchase · Add tracking & email buyer**, or **Orders → To dispatch**. The buyer, saved product names, prices and delivery address are attached to the paid order.
3. Enter the courier (optional) and HTTPS tracking link. Click **Save tracking**. Saving never sends an email. For a multi-shirt order, one shipment and link apply to all its shirts.
4. Review the displayed recipient and click **Send email**. The server uses the saved buyer email from Stripe; the form cannot choose another recipient. It refuses unsaved edits. A successful submission records the email provider's acceptance time. This is not a delivery/read confirmation.
5. Repeated clicks do not send another copy. Resending previously sent or uncertain messages requires checking the mailbox and explicitly confirming another copy. Failed authentication is recorded as failed, never sent. A worker interrupted during sending can be retried after five minutes, with the same explicit confirmation.

Sandbox orders cannot send customer emails in production. A refund does not automatically relist stock. Manually marked sold items without an online order have no buyer email or automated dispatch form.

## Production email connection

The chosen sender is **kitaly.official@outlook.com**. At initial inspection the server had SMTP host/user settings, but no password or OAuth credentials. Tracking remains usable while email sending is disabled with a clear connection message.

Outlook.com requires Modern Authentication (OAuth2), not a mailbox password. Microsoft documents [Outlook.com SMTP settings](https://support.microsoft.com/en-us/outlook/pop-imap-and-smtp-settings-for-outlook-com) and [SMTP OAuth authorization](https://learn.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth). Microsoft requires an [app registration](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app); the owner must have access to an eligible Microsoft tenant and approve access. Do not create a paid Azure subscription merely to work around an access error.

Once an owned Microsoft app is available:

1. Configure its supported account type for personal Microsoft accounts and enable public client flows for the device authorization grant. Use delegated `https://outlook.office.com/SMTP.Send` and `offline_access` permissions. Inbox-reading permission is not needed.
2. On the server, run from `/var/www/kitaly/kitaly`:

   ```bash
   venv/bin/python scripts/connect_dispatch_outlook.py --client-id YOUR_MICROSOFT_APP_CLIENT_ID
   ```

   The client ID is public configuration, not a secret. Open the displayed official Microsoft URL, enter the one-time code, sign in as the store mailbox and review consent yourself. Do not paste tokens, passwords or codes into chat.
3. The helper verifies SMTP authentication without sending any email, stores tokens in an owner-only file outside the repository, and updates the ignored server `.env`. It never prints tokens. Restart `kitaly` after successful authorization.
4. Confirm the warning has disappeared in Orders. The first real customer email must be sent by the store operator using **Send email**. No real customer or test-recipient message has been sent as part of development.

The app supports authenticated TLS SMTP for other providers, but this store's Outlook sender uses OAuth. See `.env.example` for configuration names. Refresh tokens rotate under a process lock, and token files must have owner-only permissions. Sending is claimed durably in the database before contacting SMTP so another worker cannot send concurrently.

## Deployment and verification

Back up the production database, apply migration `b83f5d21c901`, then restart the service. No changes to Stripe keys or checkout settings are needed. The customer confirmation page displays saved tracking for that customer's authenticated order session.

Dispatch tests cover saved links, sold inventory, authorization/CSRF, paid-only checks, unsafe links, escaped email content, saved recipient, language, duplicate sends, retries, failure/uncertainty, stale-worker recovery, SMTP OAuth and private token rotation. Tests use disposable inventory and mocked mail transport; they do not send real emails.
