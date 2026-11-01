"""Stripe Checkout, durable single-item reservations, and payment reconciliation."""
import hmac
import json
import secrets
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlparse

import click
import stripe
from flask import (Blueprint, abort, current_app, flash, redirect, render_template,
                   request, session, url_for, jsonify)
from flask_babel import get_locale
from sqlalchemy.exc import IntegrityError

from app.models import db, PaymentOrder, PaymentOrderItem, Shirt

payments_bp = Blueprint('payments', __name__)
SUPPORTED_CURRENCIES = {'GBP', 'EUR', 'CHF', 'USD'}


def payment_settings():
    config = current_app.config
    base = config['PUBLIC_BASE_URL'].rstrip('/')
    parsed = urlparse(base)
    key = config['STRIPE_SECRET_KEY']
    if not key.startswith(('sk_test_', 'sk_live_', 'rk_test_', 'rk_live_')):
        raise ValueError('Set STRIPE_SECRET_KEY to a Stripe test or live secret key.')
    live = key.startswith(('sk_live_', 'rk_live_'))
    if (parsed.scheme not in {'http', 'https'} or not parsed.netloc or parsed.path
            or parsed.query or parsed.fragment or parsed.username or parsed.password
            or (live and parsed.scheme != 'https')):
        raise ValueError('PUBLIC_BASE_URL must be an origin, using HTTPS for live payments.')
    if not config['STRIPE_WEBHOOK_SECRET'].startswith('whsec_'):
        raise ValueError('Set STRIPE_WEBHOOK_SECRET for the matching Stripe endpoint.')
    countries = [c.strip().upper() for c in config['STRIPE_SHIPPING_COUNTRIES'].split(',') if c.strip()]
    if not countries or any(len(c) != 2 or not c.isascii() or not c.isalpha() for c in countries):
        raise ValueError('Set STRIPE_SHIPPING_COUNTRIES to supported two-letter country codes.')
    try:
        rates = json.loads(config['STRIPE_SHIPPING_RATES'])
        if not isinstance(rates, dict) or not rates or any(
                c not in SUPPORTED_CURRENCIES or type(v) is not int or v < 0
                for c, v in rates.items()):
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('STRIPE_SHIPPING_RATES must map currencies to non-negative integer minor units.')
    return base, countries, rates, live


def payments_ready():
    if not current_app.config['STRIPE_ENABLED']:
        return False
    try:
        payment_settings()
        return True
    except ValueError:
        return False


def stripe_client():
    return stripe.StripeClient(current_app.config['STRIPE_SECRET_KEY'],
                               max_network_retries=2)


def csrf_token():
    if 'payment_csrf' not in session:
        session['payment_csrf'] = secrets.token_urlsafe(32)
    return session['payment_csrf']


def verify_csrf():
    provided = request.form.get('csrf_token', '')
    expected = session.get('payment_csrf', '')
    if not expected or not hmac.compare_digest(expected, provided):
        abort(400)


def payment_locked(shirt_id):
    # Use a current locking read on MySQL, even if a previous query opened a
    # repeatable-read snapshot before another buyer committed the reservation.
    return (PaymentOrderItem.query.filter_by(active_shirt_id=shirt_id).with_for_update().first() is not None
            or PaymentOrder.query.filter_by(active_shirt_id=shirt_id).with_for_update().first() is not None)


def can_purchase(shirt):
    if (not payments_ready() or shirt.sold or shirt.status != 'active'
            or shirt.public_price is None or not Decimal('0.50') <= shirt.public_price <= Decimal('999999.99')):
        return False
    return shirt.price_currency in payment_settings()[2]


def checkout_parameters(order, countries, base):
    italian = str(get_locale()) == 'it'
    metadata = {'order_id': order.id, 'product_code': str(order.product_code)}
    items = order.items or [order]
    return {
        'mode': 'payment', 'payment_method_types': ['card'],
        'ui_mode': 'hosted',
        'billing_address_collection': 'auto',
        'phone_number_collection': {'enabled': False},
        'automatic_tax': {'enabled': False},
        'allow_promotion_codes': False,
        'submit_type': 'auto',
        'integration_identifier': 'hosted_web_0001',
        'origin_context': 'web',
        'adaptive_pricing': {'enabled': False},
        'client_reference_id': order.id, 'metadata': metadata,
        'payment_intent_data': {'metadata': metadata},
        'line_items': [{'price_data': {
            'currency': order.currency.lower(), 'unit_amount': getattr(item, 'amount', order.amount_subtotal),
            'product_data': {'name': item.product_name,
                             'description': f'Kitaly #{item.product_code}'}}, 'quantity': 1} for item in items],
        'shipping_address_collection': {'allowed_countries': countries},
        'shipping_options': [{'shipping_rate_data': {
            'type': 'fixed_amount', 'display_name': 'Spedizione' if italian else 'Delivery',
            'fixed_amount': {'amount': order.shipping_amount, 'currency': order.currency.lower()}}}],
        'locale': 'it' if italian else 'en',
        'expires_at': int(datetime.now(timezone.utc).timestamp()) + 3600,
        'success_url': base + url_for('payments.result', order_id=order.id),
        'cancel_url': base + url_for('payments.result', order_id=order.id, cancelled=1),
    }


def apply_checkout(checkout):
    """Consume only signed webhook data or a Session retrieved directly from Stripe.

    Lock the order so concurrent/repeated deliveries are harmless. Never release
    inventory based on a browser redirect or our own clock.
    """
    order_id = (checkout.get('metadata') or {}).get('order_id')
    if not order_id:
        return None
    initial_order = db.session.get(PaymentOrder, order_id)
    if initial_order is None:
        return None
    # All inventory mutations lock shirt then order, preventing lock inversion
    # between checkout, administrative edits and concurrent webhook deliveries.
    shirt_ids = [item.shirt_id for item in initial_order.items] or [initial_order.shirt_id]
    shirts = db.session.execute(db.select(Shirt).where(Shirt.id.in_(shirt_ids)).order_by(Shirt.id)
                                .with_for_update().execution_options(populate_existing=True)).scalars().all()
    order = db.session.execute(db.select(PaymentOrder).where(
        PaymentOrder.id == order_id).with_for_update()
        .execution_options(populate_existing=True)).scalar_one_or_none()
    if order is None:
        return None
    if (checkout.get('client_reference_id') != order.id
            or checkout.get('mode') != 'payment'
            or checkout.get('livemode') != order.livemode
            or (order.checkout_session_id and order.checkout_session_id != checkout['id'])):
        raise ValueError('Checkout identity does not match the order.')
    order.checkout_session_id = checkout['id']
    if order.status == 'paid':
        db.session.commit()
        return order
    if checkout.get('payment_status') == 'paid':
        expected_total = order.amount_subtotal + order.shipping_amount
        if (checkout.get('currency', '').upper() != order.currency
                or checkout.get('amount_subtotal') != order.amount_subtotal
                or checkout.get('amount_total') != expected_total):
            order.status = 'review'
            current_app.logger.error('Payment amount mismatch for order %s', order.id)
        elif order.status != 'paid':
            if order.active_shirt_id != order.shirt_id:
                raise ValueError('Paid order no longer holds its inventory reservation.')
            if any(item.active_shirt_id != item.shirt_id for item in order.items):
                raise ValueError('Paid order lost an item reservation.')
            for shirt in shirts:
                shirt.sold = True
            order.status = 'paid'
            order.paid_at = datetime.utcnow()
            order.amount_total = checkout['amount_total']
            order.payment_intent_id = checkout.get('payment_intent')
            details = checkout.get('customer_details') or {}
            order.customer_email = details.get('email')
            order.customer_name = details.get('name')
            order.shipping_details = ((checkout.get('collected_information') or {}).get('shipping_details')
                                      or checkout.get('shipping_details'))
    elif checkout.get('status') == 'expired' and order.status not in {'paid', 'review'}:
        order.status = 'expired'
        order.active_shirt_id = None
        for item in order.items:
            item.active_shirt_id = None
    elif order.status == 'creating':
        order.status = 'pending'
    db.session.commit()
    return order


def create_checkout(order):
    checkout = stripe_client().v1.checkout.sessions.create(
        order.checkout_params, options={'idempotency_key': 'kitaly-checkout-' + order.id})
    apply_checkout(checkout)
    return checkout


@payments_bp.app_context_processor
def payment_template_helpers():
    return {'can_purchase': can_purchase, 'payment_csrf_token': csrf_token,
            'cart_count': len(cart_ids()), 'cart_ids': cart_ids()}


def cart_ids():
    raw = session.get('cart', [])
    return sorted({i for i in raw if type(i) is int and i > 0})[:20] if isinstance(raw, list) else []


def cart_response(message):
    if request.accept_mimetypes.best == 'application/json':
        return jsonify(count=len(cart_ids()), message=message)
    return redirect(url_for('payments.cart'), code=303)


@payments_bp.after_request
def private_payment_pages(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


@payments_bp.route('/cart')
def cart():
    get_locale()
    ids = cart_ids()
    shirts = Shirt.query.filter(Shirt.id.in_(ids)).order_by(Shirt.id).all() if ids else []
    if len(shirts) != len(ids):
        ids = [shirt.id for shirt in shirts]
        session['cart'] = ids
    available = [shirt for shirt in shirts if can_purchase(shirt)]
    available_ids = {shirt.id for shirt in available}
    unavailable = [shirt for shirt in shirts if shirt.id not in available_ids]
    currencies = {shirt.price_currency for shirt in available}
    currency = next(iter(currencies)) if len(currencies) == 1 else 'GBP'
    subtotal = sum(int(Decimal(shirt.public_price) * 100) for shirt in available)
    shipping = payment_settings()[2].get(currency, 0) if available else 0
    return render_template('public/cart.html', shirts=shirts, unavailable=unavailable,
                           subtotal=subtotal, shipping=shipping, currency=currency,
                           can_checkout=bool(available) and len(available)==len(ids) and len(currencies)==1)


@payments_bp.route('/cart/add/<int:shirt_id>', methods=['POST'])
def cart_add(shirt_id):
    verify_csrf()
    shirt = db.get_or_404(Shirt, shirt_id)
    if not can_purchase(shirt):
        abort(409)
    ids = cart_ids()
    if shirt_id not in ids:
        if len(ids) >= 20:
            abort(409)
        current = Shirt.query.filter(Shirt.id.in_(ids)).all() if ids else []
        if any(item.price_currency != shirt.price_currency for item in current):
            abort(409)
        ids.append(shirt_id)
    session['cart'] = ids
    return cart_response('Aggiunto al carrello' if str(get_locale())=='it' else 'Added to cart')


@payments_bp.route('/cart/remove/<int:shirt_id>', methods=['POST'])
def cart_remove(shirt_id):
    verify_csrf()
    session['cart'] = [i for i in cart_ids() if i != shirt_id]
    return cart_response('Rimosso dal carrello' if str(get_locale())=='it' else 'Removed from cart')


@payments_bp.route('/checkout/<int:shirt_id>', methods=['POST'])
def checkout(shirt_id):
    return checkout_items([shirt_id])


@payments_bp.route('/cart/checkout', methods=['POST'])
def cart_checkout():
    return checkout_items(cart_ids())


def checkout_items(ids):
    verify_csrf()
    if not payments_ready():
        abort(503)
    if not ids or len(ids)>20:
        abort(400)
    ids = sorted(set(ids))

    def lock_shirts():
        return db.session.execute(db.select(Shirt).where(Shirt.id.in_(ids)).order_by(Shirt.id)
                                  .with_for_update().execution_options(populate_existing=True)).scalars().all()

    shirts = lock_shirts()
    if len(shirts) != len(ids):
        abort(404)
    if any(not can_purchase(shirt) for shirt in shirts):
        flash('An item is no longer available. Please review your bag.', 'error')
        if request.endpoint == 'payments.checkout':
            abort(409)
        return redirect(url_for('payments.cart'), code=303)
    # Lock all shirts in ID order before looking up their reservations. This is
    # shared by single-item checkout, basket checkout, and webhook processing.
    existing_ids = {item.order_id for item in PaymentOrderItem.query.filter(
        PaymentOrderItem.active_shirt_id.in_(ids)).all()}
    existing_ids.update(order.id for order in PaymentOrder.query.filter(
        PaymentOrder.active_shirt_id.in_(ids)).all())
    if existing_ids:
        db.session.commit()
        for order_id in sorted(existing_ids):
            existing = db.session.get(PaymentOrder, order_id)
            if existing.checkout_session_id:
                try:
                    apply_checkout(stripe_client().v1.checkout.sessions.retrieve(existing.checkout_session_id))
                except stripe.StripeError:
                    current_app.logger.warning('Could not refresh order %s', existing.id)
        shirts = lock_shirts()
        conflicts = PaymentOrderItem.query.filter(PaymentOrderItem.active_shirt_id.in_(ids)).all()
        legacy = PaymentOrder.query.filter(PaymentOrder.active_shirt_id.in_(ids)).all()
        blocked = {item.order_id for item in conflicts} | {order.id for order in legacy}
        if blocked:
            for order_id in sorted(blocked):
                if order_id in session.get('payment_orders', []):
                    return redirect(url_for('payments.result', order_id=order_id), code=303)
            flash('An item is reserved by another buyer. Please review your bag or try again later.', 'error')
            return redirect(url_for('payments.cart'), code=303)
    if any(not can_purchase(shirt) for shirt in shirts):
        abort(409)
    currencies = {shirt.price_currency for shirt in shirts}
    if len(currencies) != 1:
        abort(409)
    base, countries, rates, live = payment_settings()
    first = shirts[0]
    amount = sum(int(Decimal(shirt.public_price) * 100) for shirt in shirts)
    if amount + rates[first.price_currency] > 99999999:
        abort(409)
    order = PaymentOrder(id=uuid.uuid4().hex, shirt_id=first.id, active_shirt_id=first.id,
                         product_name=f'{first.display_name} / {first.taglia}' if len(shirts)==1 else f'{len(shirts)} shirts',
                         product_code=first.product_code, currency=first.price_currency,
                         amount_subtotal=amount, shipping_amount=rates[first.price_currency],
                         livemode=live, checkout_params={})
    order.items = [PaymentOrderItem(shirt_id=shirt.id, active_shirt_id=shirt.id,
                    product_name=f'{shirt.display_name} / {shirt.taglia}', product_code=shirt.product_code,
                    amount=int(Decimal(shirt.public_price)*100)) for shirt in shirts]
    order.checkout_params = checkout_parameters(order, countries, base)
    db.session.add(order)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('An item was just reserved. Please review your bag.', 'error')
        return redirect(url_for('payments.cart'), code=303)
    session['payment_orders'] = (session.get('payment_orders', []) + [order.id])[-20:]
    try:
        checkout_session = create_checkout(order)
    except stripe.StripeError:
        db.session.rollback()
        current_app.logger.warning('Checkout creation requires reconciliation: %s', order.id)
        flash('Checkout could not be opened. Please try resuming your checkout shortly.', 'error')
        return redirect(url_for('payments.result', order_id=order.id), code=303)
    return redirect(checkout_session.url, code=303)


@payments_bp.route('/checkout/orders/<order_id>')
def result(order_id):
    if order_id not in session.get('payment_orders', []):
        abort(404)
    order = db.get_or_404(PaymentOrder, order_id)
    if order.checkout_session_id and order.status in {'creating', 'pending'}:
        try:
            apply_checkout(stripe_client().v1.checkout.sessions.retrieve(order.checkout_session_id))
        except stripe.StripeError:
            current_app.logger.warning('Could not refresh order %s', order.id)
    if order.status == 'paid':
        purchased = {item.shirt_id for item in order.items} or {order.shirt_id}
        session['cart'] = [i for i in cart_ids() if i not in purchased]
    response = current_app.make_response(render_template('public/checkout_result.html', order=order))
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    return response


@payments_bp.route('/checkout/orders/<order_id>/resume', methods=['POST'])
def resume(order_id):
    verify_csrf()
    if order_id not in session.get('payment_orders', []):
        abort(404)
    if not payments_ready():
        abort(503)
    order = db.get_or_404(PaymentOrder, order_id)
    if order.status not in {'creating', 'pending'}:
        return redirect(url_for('payments.result', order_id=order.id), code=303)
    try:
        if order.checkout_session_id:
            checkout_session = stripe_client().v1.checkout.sessions.retrieve(order.checkout_session_id)
            apply_checkout(checkout_session)
        elif datetime.now(timezone.utc).timestamp() < order.checkout_params['expires_at'] - 1800:
            checkout_session = create_checkout(order)
        else:
            flash('Please contact Kitaly with your order reference to resume this checkout.', 'error')
            return redirect(url_for('payments.result', order_id=order.id), code=303)
    except stripe.StripeError:
        db.session.rollback()
        flash('Checkout is temporarily unavailable. Please try again shortly.', 'error')
        return redirect(url_for('payments.result', order_id=order.id), code=303)
    if checkout_session.get('status') == 'open' and checkout_session.get('url'):
        return redirect(checkout_session.url, code=303)
    return redirect(url_for('payments.result', order_id=order.id), code=303)


@payments_bp.route('/stripe/webhook', methods=['POST'])
def webhook():
    secret = current_app.config['STRIPE_WEBHOOK_SECRET']
    if not secret:
        abort(503)
    try:
        event = stripe.Webhook.construct_event(request.get_data(),
                                              request.headers.get('Stripe-Signature', ''), secret)
    except (ValueError, stripe.SignatureVerificationError):
        abort(400)
    if event['type'] in {'checkout.session.completed', 'checkout.session.expired',
                         'checkout.session.async_payment_succeeded', 'checkout.session.async_payment_failed'}:
        try:
            apply_checkout(event['data']['object'])
        except ValueError:
            db.session.rollback()
            current_app.logger.exception('Stripe order validation failed')
            abort(400)
    return '', 200


def register_payment_commands(app):
    @app.cli.group('payments')
    def payments():
        """Check configuration and reconcile Stripe orders."""

    @payments.command('check')
    def check():
        try:
            _, countries, rates, live = payment_settings()
        except ValueError as error:
            raise click.ClickException(str(error))
        click.echo(f"Configuration valid: {'LIVE' if live else 'TEST'}; checkout enabled: {app.config['STRIPE_ENABLED']}")
        click.echo(f"Shipping countries: {', '.join(countries)}; minor-unit rates: {rates}")

    @payments.command('reconcile')
    def reconcile():
        """Recover missed webhooks and uncertain Session creation without releasing live inventory."""
        _, _, _, live = payment_settings()
        client = stripe_client()
        orders = PaymentOrder.query.filter(PaymentOrder.status.in_(['creating', 'pending'])).all()
        for order in orders:
            if order.livemode != live:
                click.echo(f'{order.id}: skipped; configure the matching test/live key to reconcile.')
                continue
            if order.checkout_session_id:
                apply_checkout(client.v1.checkout.sessions.retrieve(order.checkout_session_id))
            else:
                # A process may have stopped after Stripe accepted Session creation.
                start = int(order.created_at.replace(tzinfo=timezone.utc).timestamp()) - 300
                matches = client.v1.checkout.sessions.list({'created': {'gte': start}, 'limit': 100})
                found = False
                for checkout_session in matches.auto_paging_iter():
                    if checkout_session.get('client_reference_id') == order.id:
                        apply_checkout(checkout_session)
                        found = True
                        break
                if not found:
                    click.echo(f'{order.id}: no Stripe Session found; reservation retained. Check Stripe before release.')
                    continue
            click.echo(f'{order.id}: {order.status}')

    @payments.command('release-uncreated')
    @click.argument('order_id')
    def release_uncreated(order_id):
        """Release a failed creation only after its creation window has closed.

        Existing Stripe Sessions are reconciled instead, never blindly released.
        """
        _, _, _, live = payment_settings()
        order = db.session.get(PaymentOrder, order_id)
        if order is None or order.status != 'creating' or order.checkout_session_id:
            raise click.ClickException('Only an order without a known Stripe Session can be released.')
        if order.livemode != live:
            raise click.ClickException('Configure the matching test/live Stripe key before releasing inventory.')
        if datetime.now(timezone.utc).timestamp() <= order.checkout_params['expires_at'] + 300:
            raise click.ClickException('Wait until five minutes after the checkout expiry before release.')
        start = int(order.created_at.replace(tzinfo=timezone.utc).timestamp()) - 300
        matches = stripe_client().v1.checkout.sessions.list({'created': {'gte': start}, 'limit': 100})
        for checkout_session in matches.auto_paging_iter():
            if checkout_session.get('client_reference_id') == order.id:
                apply_checkout(checkout_session)
                click.echo(f'{order.id}: Stripe Session found and reconciled; status {order.status}.')
                return
        order = db.session.execute(db.select(PaymentOrder).where(PaymentOrder.id == order_id)
                                   .with_for_update().execution_options(populate_existing=True)).scalar_one()
        if order.status != 'creating' or order.checkout_session_id:
            raise click.ClickException('Order changed during reconciliation; reservation retained.')
        order.status = 'failed'
        order.active_shirt_id = None
        for item in order.items:
            item.active_shirt_id = None
        db.session.commit()
        click.echo(f'{order.id}: no Stripe Session exists; failed reservation released.')
