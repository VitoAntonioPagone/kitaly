import os
import smtplib
import tempfile
import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock


class DispatchTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'DATABASE_URL':'sqlite:///'+self.directory.name+'/db',
            'SECRET_KEY':'dispatch-tests','UPLOAD_FOLDER':self.directory.name+'/uploads',
            'ADMIN_URL_PREFIX':'admin'})
        self.env.start()
        from app import create_app
        from app.models import db, Shirt, PaymentOrder, PaymentOrderItem
        self.db,self.Shirt,self.Order=db,Shirt,PaymentOrder
        self.app=create_app();self.app.config.update(TESTING=True,SMTP_HOST='smtp.example.com',
            SMTP_PORT='587',SMTP_USER='store@example.com',SMTP_FROM='store@example.com',
            SMTP_PASSWORD='test-only',SMTP_OAUTH_CLIENT_ID='',SMTP_OAUTH_TOKEN_FILE='')
        with self.app.app_context():
            db.create_all()
            sold=Shirt(product_code=200,brand='Nike',squadra='Italy',campionato='',taglia='L',colore='Blue',stagione='1998',sold=True,status='active',public_price=Decimal('40'),price_currency='GBP')
            available=Shirt(product_code=201,brand='Adidas',squadra='Milan',campionato='',taglia='M',colore='Red',stagione='2001',sold=False,status='active')
            db.session.add_all([sold,available]);db.session.flush();self.sold_id=sold.id
            order=PaymentOrder(id='paid-dispatch-order',shirt_id=sold.id,active_shirt_id=sold.id,
                product_name='Italy Nike 1998 / L',product_code=200,amount_subtotal=4000,
                shipping_amount=650,currency='GBP',status='paid',checkout_params={'locale':'en'},
                customer_email='buyer@example.com',customer_name='Test Buyer',livemode=True,paid_at=datetime.utcnow())
            order.items=[PaymentOrderItem(shirt_id=sold.id,active_shirt_id=sold.id,product_name=order.product_name,product_code=200,amount=4000)]
            db.session.add(order);db.session.commit();self.order_id=order.id
        self.client=self.app.test_client()
        with self.client.session_transaction() as session: session['logged_in']=True;session['payment_csrf']='dispatch-csrf'
        self.smtp_patch=patch('app.dispatch_mail.smtplib.SMTP');self.smtp=self.smtp_patch.start().return_value
        self.smtp.send_message.return_value={}
        self.values={'csrf_token':'dispatch-csrf','shipping_carrier':'Royal Mail','tracking_url':'https://www.royalmail.com/track-your-item#/tracking-results/TEST123'}

    def tearDown(self):
        self.smtp_patch.stop()
        with self.app.app_context():self.db.session.remove();self.db.engine.dispose()
        self.env.stop();self.directory.cleanup()

    def post(self, action, **extra):
        return self.client.post('/admin/orders/'+self.order_id+'/'+action,data=dict(self.values,**extra))

    def save(self):
        self.assertEqual(self.post('tracking').status_code,303)

    def test_paid_sale_moves_to_sold_and_shows_buyer_dispatch_controls(self):
        available=self.client.get('/admin/').get_data(as_text=True)
        self.assertNotIn('buyer@example.com',available)
        sold=self.client.get('/admin/?sold_filter=yes').get_data(as_text=True)
        self.assertIn('buyer@example.com',sold);self.assertIn('Save tracking',sold);self.assertIn('Send email',sold)
        self.assertIn('To dispatch',self.client.get('/admin/orders?dispatch=pending').get_data(as_text=True))

    def test_save_persists_without_sending_then_email_uses_saved_buyer_and_items(self):
        self.save();self.smtp.send_message.assert_not_called()
        self.assertEqual(self.post('send-dispatch').status_code,303)
        message=self.smtp.send_message.call_args.args[0]
        self.assertEqual(message['To'],'buyer@example.com')
        self.assertIn('Italy Nike 1998',message.get_body(preferencelist=('plain',)).get_content())
        self.assertIn(self.values['tracking_url'],message.get_body(preferencelist=('plain',)).get_content())
        self.smtp.starttls.assert_called_once();self.smtp.login.assert_called_once_with('store@example.com','test-only')
        with self.app.app_context():
            order=self.db.session.get(self.Order,self.order_id)
            self.assertEqual(order.tracking_email_state,'sent');self.assertIsNotNone(order.tracking_email_sent_at)
            self.assertTrue(self.db.session.get(self.Shirt,self.sold_id).sold)

    def test_double_click_cannot_send_twice_and_resend_requires_confirmation(self):
        self.save();self.post('send-dispatch');self.post('send-dispatch')
        self.assertEqual(self.smtp.send_message.call_count,1)
        self.post('send-dispatch',confirm_resend='yes');self.assertEqual(self.smtp.send_message.call_count,2)

    def test_unsaved_changes_do_not_get_emailed(self):
        self.save();self.post('send-dispatch',tracking_url='https://www.royalmail.com/new-link')
        self.smtp.send_message.assert_not_called()

    def test_invalid_links_unpaid_orders_and_missing_csrf_are_rejected(self):
        for url in ['javascript:alert(1)','http://www.royalmail.com','https://user:password@www.royalmail.com','https://www.royalmail.com/\nFake: header','https://localhost']:
            self.post('tracking',tracking_url=url)
            with self.app.app_context():self.assertIsNone(self.db.session.get(self.Order,self.order_id).tracking_url)
        self.assertEqual(self.client.post('/admin/orders/'+self.order_id+'/tracking',data={}).status_code,400)
        with self.app.app_context():
            order=self.db.session.get(self.Order,self.order_id);order.status='pending';self.db.session.commit()
        self.assertEqual(self.post('tracking').status_code,409);self.assertEqual(self.post('send-dispatch').status_code,409)
        self.smtp.send_message.assert_not_called()

    def test_unauthenticated_requests_cannot_access_or_send(self):
        client=self.app.test_client()
        self.assertEqual(client.get('/admin/orders').status_code,302)
        self.assertEqual(client.post('/admin/orders/'+self.order_id+'/tracking',data=self.values).status_code,302)
        self.assertEqual(client.post('/admin/orders/'+self.order_id+'/send-dispatch',data=self.values).status_code,302)
        self.smtp.send_message.assert_not_called()

    def test_missing_outlook_connection_blocks_email_but_not_tracking_save(self):
        self.app.config.update(SMTP_HOST='smtp-mail.outlook.com',SMTP_USER='kitaly.official@outlook.com',SMTP_PASSWORD='')
        self.save();self.post('send-dispatch')
        self.smtp.send_message.assert_not_called()
        page=self.client.get('/admin/orders').get_data(as_text=True);self.assertIn('secure OAuth connection',page)
        with self.app.app_context():self.assertIsNotNone(self.db.session.get(self.Order,self.order_id).tracking_url)

    def test_smtp_auth_failure_records_failure_and_never_claims_sent(self):
        self.save();self.smtp.login.side_effect=smtplib.SMTPAuthenticationError(535,b'no')
        self.post('send-dispatch')
        with self.app.app_context():
            order=self.db.session.get(self.Order,self.order_id);self.assertEqual(order.tracking_email_state,'failed');self.assertIsNone(order.tracking_email_sent_at)
        self.smtp.send_message.assert_not_called()

    def test_uncertain_smtp_delivery_requires_checked_resend(self):
        self.save();self.smtp.send_message.side_effect=smtplib.SMTPServerDisconnected('after DATA')
        self.post('send-dispatch')
        with self.app.app_context():
            order=self.db.session.get(self.Order,self.order_id);self.assertEqual(order.tracking_email_state,'unknown');self.assertIsNone(order.tracking_email_sent_at)
        self.post('send-dispatch');self.assertEqual(self.smtp.send_message.call_count,1)
        self.smtp.send_message.side_effect=None;self.smtp.send_message.return_value={}
        self.post('send-dispatch',confirm_resend='yes');self.assertEqual(self.smtp.send_message.call_count,2)

    def test_active_send_blocks_changes_and_stale_send_needs_confirmation(self):
        self.save()
        with self.app.app_context():
            order=self.db.session.get(self.Order,self.order_id);order.tracking_email_state='sending';order.tracking_email_started_at=datetime.utcnow();self.db.session.commit()
        self.post('send-dispatch');self.smtp.send_message.assert_not_called()
        self.post('tracking',tracking_url='https://www.royalmail.com/changed')
        with self.app.app_context():
            order=self.db.session.get(self.Order,self.order_id);self.assertEqual(order.tracking_url,self.values['tracking_url']);order.tracking_email_started_at=datetime.utcnow()-timedelta(minutes=6);self.db.session.commit()
        self.post('send-dispatch');self.smtp.send_message.assert_not_called()
        self.post('send-dispatch',confirm_resend='yes');self.smtp.send_message.assert_called_once()

    def test_update_tracking_preserves_history_and_requires_new_explicit_send(self):
        self.save();self.post('send-dispatch')
        new='https://www.royalmail.com/replacement';self.post('tracking',tracking_url=new)
        with self.app.app_context():
            order=self.db.session.get(self.Order,self.order_id);self.assertEqual(order.tracking_email_state,'draft');self.assertIsNotNone(order.tracking_email_sent_at)
        self.post('send-dispatch',tracking_url=new);self.assertEqual(self.smtp.send_message.call_count,2)

    def test_message_escapes_html_and_uses_checkout_language(self):
        from app.dispatch_mail import dispatch_message
        self.save()
        with self.app.app_context():
            order=self.db.session.get(self.Order,self.order_id);order.customer_name='<script>buyer</script>';order.checkout_params={'locale':'it'}
            message=dispatch_message(order);self.assertIn('spedito',message['Subject'])
            body=message.get_body(preferencelist=('html',)).get_content();self.assertNotIn('<script>',body);self.assertIn('&lt;script&gt;',body)

    def test_outlook_oauth_authenticates_without_a_mailbox_password(self):
        import json,time
        from pathlib import Path
        token_file=Path(self.directory.name)/'outlook.json'
        token_file.write_text(json.dumps({'access_token':'test-access-token','refresh_token':'test-refresh','expires_at':time.time()+3600}))
        token_file.chmod(0o600)
        self.app.config.update(SMTP_USER='store@outlook.com',SMTP_FROM='store@outlook.com',SMTP_PASSWORD='',
            SMTP_OAUTH_CLIENT_ID='test-client',SMTP_OAUTH_TOKEN_FILE=str(token_file))
        self.smtp.docmd.return_value=(235,b'OK')
        self.save();self.post('send-dispatch')
        self.smtp.login.assert_not_called();self.smtp.send_message.assert_called_once()
        with self.app.app_context():self.assertEqual(self.db.session.get(self.Order,self.order_id).tracking_email_state,'sent')

    def test_outlook_refresh_rotates_token_privately_and_denies_world_readable_token_file(self):
        import io,json
        from pathlib import Path
        from app.dispatch_mail import outlook_access_token,DispatchMailError
        path=Path(self.directory.name)/'oauth.json';path.write_text(json.dumps({'refresh_token':'old'}));path.chmod(0o600)
        self.app.config.update(SMTP_OAUTH_CLIENT_ID='client',SMTP_OAUTH_TOKEN_FILE=str(path))
        with self.app.app_context(),patch('app.dispatch_mail.urlopen',return_value=io.BytesIO(json.dumps({'access_token':'new','refresh_token':'rotated','expires_in':3600}).encode())):
            self.assertEqual(outlook_access_token(),'new')
        self.assertEqual(json.loads(path.read_text())['refresh_token'],'rotated');self.assertEqual(path.stat().st_mode & 0o777,0o600)
        path.chmod(0o644)
        with self.app.app_context():
            with self.assertRaises(DispatchMailError):outlook_access_token()

    def test_dispatch_retains_purchase_snapshot_after_inventory_edit(self):
        # Dispatch content uses the purchased snapshots, not a later product edit.
        self.save()
        with self.app.app_context():
            shirt=self.db.session.get(self.Shirt,self.sold_id);shirt.squadra='Changed title';self.db.session.commit()
        self.post('send-dispatch')
        message=self.smtp.send_message.call_args.args[0]
        self.assertIn('Italy Nike 1998',message.get_body(preferencelist=('plain',)).get_content())
