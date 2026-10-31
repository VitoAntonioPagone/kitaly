import hashlib
import hmac
import json
import os
import tempfile
import time
import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

import stripe


class PaymentsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            'DATABASE_URL': 'sqlite:///' + self.directory.name + '/test.db',
            'SECRET_KEY': 'payment-tests', 'UPLOAD_FOLDER': self.directory.name + '/uploads',
            'ADMIN_URL_PREFIX': 'admin', 'STRIPE_ENABLED': 'true',
            'STRIPE_SECRET_KEY': 'sk_test_placeholder', 'STRIPE_WEBHOOK_SECRET': 'whsec_placeholder',
            'PUBLIC_BASE_URL': 'http://localhost', 'STRIPE_SHIPPING_COUNTRIES': 'GB,IT',
            'STRIPE_SHIPPING_RATES': '{"GBP":500}',
        })
        self.env.start()
        from app import create_app
        from app.models import db, Shirt, PaymentOrder
        self.db, self.Shirt, self.Order = db, Shirt, PaymentOrder
        self.app = create_app()
        self.app.config['TESTING'] = True
        with self.app.app_context():
            db.create_all()
            shirt = Shirt(product_code=42, brand='Nike', squadra='Italy', campionato='',
                          taglia='L', colore='Blue', stagione='1998', status='active',
                          public_price=Decimal('40.50'), price_currency='GBP')
            db.session.add(shirt)
            db.session.commit()
            self.shirt_id = shirt.id
        self.client = self.app.test_client()
        self.api = MagicMock()
        self.sdk_patch = patch('app.payments.stripe_client', return_value=self.api)
        self.sdk_patch.start()
        self.sessions = self.api.v1.checkout.sessions
        self.sessions.create.side_effect = self.fake_create

    def tearDown(self):
        self.sdk_patch.stop()
        with self.app.app_context():
            self.db.session.remove()
            self.db.engine.dispose()
        self.env.stop()
        self.directory.cleanup()

    def token(self, client=None):
        client = client or self.client
        with client.session_transaction() as session:
            session['payment_csrf'] = 'test-csrf'
        return {'csrf_token': 'test-csrf'}

    def fake_create(self, params, options):
        result = stripe.StripeObject.construct_from({
            'id': 'cs_test_order', 'object': 'checkout.session', 'mode': 'payment',
            'livemode': False, 'metadata': params['metadata'],
            'client_reference_id': params['client_reference_id'],
            'status': 'open', 'payment_status': 'unpaid', 'currency': 'gbp',
            'amount_subtotal': 4050, 'amount_total': 4550,
            'url': 'https://checkout.stripe.com/c/pay/test'}, None)
        self.checkout_session = result
        self.sessions.retrieve.return_value = result
        return result

    def start(self):
        response = self.client.post(f'/checkout/{self.shirt_id}', data=self.token())
        self.assertEqual(response.status_code, 303)
        with self.app.app_context():
            self.order_id = self.Order.query.one().id
        return response

    def webhook(self, kind='checkout.session.completed', **updates):
        checkout = dict(self.checkout_session)
        checkout.update(updates)
        body = json.dumps({'id': 'evt_test', 'type': kind, 'data': {'object': checkout}})
        timestamp = str(int(time.time()))
        signature = hmac.new(b'whsec_placeholder', (timestamp + '.' + body).encode(), hashlib.sha256).hexdigest()
        return self.client.post('/stripe/webhook', data=body, content_type='application/json',
                                headers={'Stripe-Signature': f't={timestamp},v1={signature}'})

    def pay(self, **extra):
        values = dict(status='complete', payment_status='paid', payment_intent='pi_test_order',
                      customer_details={'name': 'Buyer', 'email': 'buyer@example.com'},
                      collected_information={'shipping_details': {'name': 'Buyer',
                                             'address': {'line1': '1 Street', 'country': 'GB'}}})
        values.update(extra)
        return self.webhook(**values)

    def test_checkout_uses_database_price_and_explicit_shipping(self):
        with self.client.session_transaction(base_url='http://attacker.example') as browser_session:
            browser_session['payment_csrf'] = 'test-csrf'
        response = self.client.post(f'/checkout/{self.shirt_id}',
                                    data=dict(csrf_token='test-csrf', amount='1', currency='usd'),
                                    headers={'Host': 'attacker.example'})
        self.assertEqual(response.status_code, 303)
        params = self.sessions.create.call_args.args[0]
        self.assertEqual(params['line_items'][0]['price_data']['unit_amount'], 4050)
        self.assertEqual(params['shipping_options'][0]['shipping_rate_data']['fixed_amount'],
                         {'amount': 500, 'currency': 'gbp'})
        self.assertEqual(params['shipping_address_collection']['allowed_countries'], ['GB', 'IT'])
        self.assertTrue(params['success_url'].startswith('http://localhost/'))
        self.assertEqual(params['payment_method_types'], ['card'])

    def test_signed_payment_marks_sold_and_records_delivery_once(self):
        self.start()
        self.assertEqual(self.pay().status_code, 200)
        self.assertEqual(self.pay().status_code, 200)
        self.assertEqual(self.webhook('checkout.session.expired', status='expired').status_code, 200)
        with self.app.app_context():
            order = self.Order.query.one()
            self.assertEqual(order.status, 'paid')
            self.assertEqual(order.amount_total, 4550)
            self.assertEqual(order.customer_email, 'buyer@example.com')
            self.assertEqual(order.shipping_details['address']['country'], 'GB')
            self.assertEqual(order.active_shirt_id, self.shirt_id)
            self.assertTrue(self.db.session.get(self.Shirt, self.shirt_id).sold)

    def test_unsigned_and_wrong_amount_cannot_fulfill(self):
        self.start()
        self.assertEqual(self.client.post('/stripe/webhook', json={}).status_code, 400)
        self.assertEqual(self.pay(amount_total=1).status_code, 200)
        with self.app.app_context():
            self.assertEqual(self.Order.query.one().status, 'review')
            self.assertFalse(self.db.session.get(self.Shirt, self.shirt_id).sold)
            self.assertIsNotNone(self.Order.query.one().active_shirt_id)

    def test_identity_and_mode_mismatch_are_rejected(self):
        self.start()
        for change in [{'livemode': True}, {'client_reference_id': 'other'}, {'id': 'cs_other'}, {'mode': 'subscription'}]:
            with self.subTest(change=change):
                self.assertEqual(self.pay(**change).status_code, 400)
        with self.app.app_context():
            self.assertEqual(self.Order.query.one().status, 'pending')

    def test_cancel_redirect_does_not_release_or_mark_paid(self):
        self.start()
        response = self.client.get(f'/checkout/orders/{self.order_id}?cancelled=1')
        self.assertIn(b'Payment not yet confirmed', response.data)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        with self.app.app_context():
            self.assertEqual(self.Order.query.one().active_shirt_id, self.shirt_id)
            self.assertFalse(self.db.session.get(self.Shirt, self.shirt_id).sold)

    def test_confirmation_retrieves_stripe_when_webhook_is_delayed(self):
        self.start()
        self.checkout_session.update({'status': 'complete', 'payment_status': 'paid'})
        response = self.client.get(f'/checkout/orders/{self.order_id}')
        self.assertIn(b'Payment received', response.data)
        with self.app.app_context():
            self.assertTrue(self.db.session.get(self.Shirt, self.shirt_id).sold)

    def test_other_buyer_cannot_access_order_or_buy_reserved_item(self):
        self.start()
        other = self.app.test_client()
        self.assertEqual(other.get(f'/checkout/orders/{self.order_id}').status_code, 404)
        response = other.post(f'/checkout/{self.shirt_id}', data=self.token(other))
        self.assertEqual(response.status_code, 303)
        self.assertNotIn(self.order_id, response.location)
        self.assertEqual(self.sessions.create.call_count, 1)
        response = self.client.post(f'/checkout/{self.shirt_id}', data=self.token())
        self.assertIn(self.order_id, response.location)
        self.assertEqual(self.sessions.create.call_count, 1)

    def test_expiration_releases_reservation(self):
        self.start()
        self.assertEqual(self.webhook('checkout.session.expired', status='expired').status_code, 200)
        with self.app.app_context():
            self.assertEqual(self.Order.query.one().status, 'expired')
            self.assertIsNone(self.Order.query.one().active_shirt_id)
            self.assertFalse(self.db.session.get(self.Shirt, self.shirt_id).sold)

    def test_creation_timeout_keeps_reservation_and_retries_same_key(self):
        self.sessions.create.side_effect = stripe.APIConnectionError('timeout')
        self.start()
        first = self.sessions.create.call_args
        with self.app.app_context():
            order = self.Order.query.one()
            self.assertEqual(order.status, 'creating')
            self.assertEqual(order.active_shirt_id, self.shirt_id)
        self.sessions.create.side_effect = self.fake_create
        response = self.client.post(f'/checkout/orders/{self.order_id}/resume', data=self.token())
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.sessions.create.call_args, first)

    def test_gate_csrf_sold_hidden_and_price_on_request(self):
        self.assertEqual(self.client.post(f'/checkout/{self.shirt_id}').status_code, 400)
        for changes in [{'sold': True}, {'status': 'hidden'}, {'public_price': None}, {'public_price': 0}, {'price_currency': 'EUR'}]:
            with self.subTest(changes=changes):
                with self.app.app_context():
                    shirt = self.db.session.get(self.Shirt, self.shirt_id)
                    shirt.sold, shirt.status, shirt.public_price, shirt.price_currency = False, 'active', Decimal('40.50'), 'GBP'
                    for key, value in changes.items():
                        setattr(shirt, key, value)
                    self.db.session.commit()
                self.assertEqual(self.client.post(f'/checkout/{self.shirt_id}', data=self.token()).status_code, 409)
        self.app.config['STRIPE_ENABLED'] = False
        self.assertEqual(self.client.post(f'/checkout/{self.shirt_id}', data=self.token()).status_code, 503)
        self.sessions.create.assert_not_called()

    def test_configuration_and_button(self):
        page = self.client.get(f'/shirt/{self.shirt_id}', follow_redirects=True).data
        self.assertIn(b'Buy now', page)
        self.app.config['STRIPE_SHIPPING_RATES'] = '{}'
        page = self.client.get(f'/shirt/{self.shirt_id}', follow_redirects=True).data
        self.assertNotIn(b'Buy now', page)
        self.assertEqual(self.app.test_cli_runner().invoke(args=['payments', 'check']).exit_code, 1)

    def test_admin_orders_require_login_and_inventory_is_locked(self):
        self.start()
        self.assertEqual(self.client.get('/admin/orders').status_code, 302)
        with self.client.session_transaction() as session:
            session['logged_in'] = True
        self.assertIn(self.order_id.encode(), self.client.get('/admin/orders').data)
        self.assertEqual(self.client.post(f'/admin/toggle_sold/{self.shirt_id}').status_code, 409)
        self.assertEqual(self.client.post(f'/admin/update_pricing/{self.shirt_id}', data={'public_price': '1'}).status_code, 409)
        self.assertEqual(self.client.post(f'/admin/edit/{self.shirt_id}', data={}).status_code, 302)
        self.assertEqual(self.client.post(f'/admin/delete/{self.shirt_id}').status_code, 302)
        with self.app.app_context():
            self.assertIsNotNone(self.db.session.get(self.Shirt, self.shirt_id))

    def test_reconciliation_recovers_session_after_creation_crash(self):
        self.sessions.create.side_effect = stripe.APIConnectionError('timeout')
        self.start()
        with self.app.app_context():
            params = self.Order.query.one().checkout_params
        recovered = self.fake_create(params, {})
        recovered.update({'status': 'expired'})
        self.sessions.list.return_value.auto_paging_iter.return_value = iter([recovered])
        result = self.app.test_cli_runner().invoke(args=['payments', 'reconcile'])
        self.assertEqual(result.exit_code, 0, result.output)
        with self.app.app_context():
            self.assertEqual(self.Order.query.one().status, 'expired')
            self.assertIsNone(self.Order.query.one().active_shirt_id)

    def test_database_rejects_two_active_reservations_for_one_item(self):
        from sqlalchemy.exc import IntegrityError
        self.start()
        with self.app.app_context():
            order = self.Order.query.one()
            duplicate = self.Order(id='another-order', shirt_id=self.shirt_id,
                                   active_shirt_id=self.shirt_id, product_name='Duplicate',
                                   product_code=42, amount_subtotal=4050, shipping_amount=500,
                                   currency='GBP', checkout_params={}, livemode=False)
            self.db.session.add(duplicate)
            with self.assertRaises(IntegrityError):
                self.db.session.commit()
            self.db.session.rollback()

    def test_failed_creation_release_waits_and_checks_stripe(self):
        self.sessions.create.side_effect = stripe.APIConnectionError('timeout')
        self.start()
        runner = self.app.test_cli_runner()
        args = ['payments', 'release-uncreated', self.order_id]
        self.assertEqual(runner.invoke(args=args).exit_code, 1)
        with self.app.app_context():
            order = self.Order.query.one()
            params = dict(order.checkout_params)
            params['expires_at'] = int(time.time()) - 600
            order.checkout_params = params
            self.db.session.commit()
        self.sessions.list.return_value.auto_paging_iter.return_value = iter([])
        result = runner.invoke(args=args)
        self.assertEqual(result.exit_code, 0, result.output)
        with self.app.app_context():
            self.assertEqual(self.Order.query.one().status, 'failed')
            self.assertIsNone(self.Order.query.one().active_shirt_id)

    def test_mismatched_mode_cannot_release_reservation(self):
        self.sessions.create.side_effect = stripe.APIConnectionError('timeout')
        self.start()
        self.app.config['STRIPE_SECRET_KEY'] = 'sk_live_placeholder'
        self.app.config['PUBLIC_BASE_URL'] = 'https://example.com'
        result = self.app.test_cli_runner().invoke(args=['payments', 'release-uncreated', self.order_id])
        self.assertEqual(result.exit_code, 1)
        self.assertIn('matching test/live', result.output)
        with self.app.app_context():
            self.assertIsNotNone(self.Order.query.one().active_shirt_id)


if __name__ == '__main__':
    unittest.main()
