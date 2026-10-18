import os
import shutil
import tempfile
import unittest
from decimal import Decimal
from html import unescape
from unittest.mock import patch


class PublicPricingTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.env = patch.dict(os.environ, {
            'DATABASE_URL': 'sqlite:///' + self.directory + '/test.db',
            'SECRET_KEY': 'pricing-test', 'UPLOAD_FOLDER': self.directory + '/uploads',
            'ADMIN_URL_PREFIX': 'admin',
        })
        self.env.start()
        from app import create_app
        from app.models import db, Shirt
        self.db, self.Shirt = db, Shirt
        self.app = create_app()
        self.app.config['TESTING'] = True
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session['logged_in'] = True

    def tearDown(self):
        with self.app.app_context():
            self.db.session.remove()
            self.db.engine.dispose()
        self.env.stop()
        shutil.rmtree(self.directory)

    def form(self, **changes):
        values = dict(brand='Nike', squadra='Italy', campionato='National Teams', taglia='L',
                      colore='Blue', stagione='1998/1999', type='Shirt', player_name='Baggio',
                      prezzo_pagato='12.34', internal_price='98.76', public_price='40.50',
                      price_currency='GBP', descrizione='', status='active')
        values.update(changes)
        return values

    def create(self, **changes):
        response = self.client.post('/admin/new', data=self.form(**changes))
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            return self.Shirt.query.one().id

    def test_create_edit_and_clear_public_price(self):
        shirt_id = self.create()
        with self.app.app_context():
            shirt = self.db.session.get(self.Shirt, shirt_id)
            self.assertEqual(shirt.public_price, Decimal('40.50'))
            self.assertEqual(shirt.to_dict()['public_price'], '40.50')
        for path in ['/catalogue', f'/shirt/{shirt_id}']:
            page = self.client.get(path, follow_redirects=True).get_data(as_text=True)
            self.assertIn('£40.50', page)
            self.assertNotIn('12.34', page)
            self.assertNotIn('98.76', page)
        response = self.client.post(f'/admin/edit/{shirt_id}', data=self.form(public_price='62.00', price_currency='EUR'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('€62.00', self.client.get('/catalogue').get_data(as_text=True))
        response = self.client.post(f'/admin/edit/{shirt_id}', data=self.form(public_price=''))
        self.assertEqual(response.status_code, 302)
        self.assertIn(b'Price on request', self.client.get('/catalogue').data)

    def test_dashboard_price_updates_preserve_private_prices(self):
        shirt_id = self.create()
        response = self.client.post(f'/admin/update_pricing/{shirt_id}', data={'public_price':'0', 'price_currency':'CHF'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['public_price'], '0.00')
        with self.app.app_context():
            shirt = self.db.session.get(self.Shirt, shirt_id)
            self.assertEqual(shirt.prezzo_pagato, 12.34)
            self.assertEqual(shirt.internal_price, Decimal('98.76'))
        response = self.client.post(f'/admin/update_pricing/{shirt_id}', data={'public_price':''})
        self.assertIsNone(response.json['public_price'])

    def test_invalid_prices_are_rejected_atomically(self):
        shirt_id = self.create()
        for value in ['-1', 'NaN', 'Infinity', 'garbage', '1.234', '100000000']:
            with self.subTest(value=value):
                response = self.client.post(f'/admin/update_pricing/{shirt_id}', data={'public_price':value, 'price_paid':'500'})
                self.assertEqual(response.status_code, 400)
                with self.app.app_context():
                    shirt = self.db.session.get(self.Shirt, shirt_id)
                    self.assertEqual(shirt.public_price, Decimal('40.50'))
                    self.assertEqual(shirt.prezzo_pagato, 12.34)
        response = self.client.post(f'/admin/update_pricing/{shirt_id}', data={'public_price':'90', 'price_currency':'BAD'})
        self.assertEqual(response.status_code, 400)
        with self.app.app_context():
            self.assertEqual(self.db.session.get(self.Shirt, shirt_id).public_price, Decimal('40.50'))

    def test_invalid_create_does_not_create_product(self):
        response = self.client.post('/admin/new', data=self.form(public_price='-40'))
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertEqual(self.Shirt.query.count(), 0)

    def test_prices_require_admin_session(self):
        shirt_id = self.create()
        with self.client.session_transaction() as session:
            session.clear()
        response = self.client.post(f'/admin/update_pricing/{shirt_id}', data={'public_price':'1'})
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertEqual(self.db.session.get(self.Shirt, shirt_id).public_price, Decimal('40.50'))

    def test_default_english_explicit_italian_and_filter_preservation(self):
        self.create()
        response = self.client.get('/catalogue?brand=Nike&brand=Adidas', headers={'Accept-Language':'it-IT,it;q=0.9'})
        page = unescape(response.get_data(as_text=True))
        self.assertIn('<html lang="en">', page)
        self.assertIn('brand=Nike&brand=Adidas&lang=it', page)
        italian = self.client.get('/catalogue?lang=it').get_data(as_text=True)
        self.assertIn('<html lang="it">', italian)
        self.assertIn('40,50', italian)
        self.assertIn('<html lang="it">', self.client.get('/catalogue').get_data(as_text=True))

    def test_search_player_and_season_and_unique_admin_fields(self):
        shirt_id = self.create()
        for query in ['Baggio', '1998']:
            self.assertIn('£40.50', self.client.get('/catalogue', query_string={'q':query}).get_data(as_text=True))
        for path in ['/admin/new', f'/admin/edit/{shirt_id}']:
            page = self.client.get(path).get_data(as_text=True)
            self.assertEqual(page.count('id="public-price"'), 1)
            self.assertEqual(page.count('id="price-currency"'), 1)
        page = self.client.get('/admin/').get_data(as_text=True)
        self.assertIn('Public price', page)


if __name__ == '__main__':
    unittest.main()
