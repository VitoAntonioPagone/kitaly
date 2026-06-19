import os
import tempfile
import unittest


class VintedUrlFlowTestCase(unittest.TestCase):
    def setUp(self):
        self.database_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.database_file.close()
        self.upload_dir = tempfile.mkdtemp()

        os.environ['DATABASE_URL'] = f'sqlite:///{self.database_file.name}'
        os.environ['SECRET_KEY'] = 'test-secret'
        os.environ['UPLOAD_FOLDER'] = self.upload_dir

        from app import create_app
        from app.models import db

        self.db = db
        self.app = create_app()
        self.app.config.update(TESTING=True)
        with self.app.app_context():
            self.db.create_all()

        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session['logged_in'] = True

    def tearDown(self):
        with self.app.app_context():
            self.db.session.remove()
            self.db.drop_all()
        os.unlink(self.database_file.name)

    @staticmethod
    def product_form(**overrides):
        values = {
            'player_name': '',
            'brand': 'Nike',
            'squadra': 'Italy',
            'campionato': 'National Teams',
            'taglia': 'L',
            'colore': 'Blue',
            'stagione': '2025-26',
            'tipologia': '',
            'type': 'Shirt',
            'maniche': '',
            'prezzo_pagato': '',
            'internal_price': '',
            'descrizione': '',
            'descrizione_ita': '',
            'status': 'active',
        }
        values.update(overrides)
        return values

    def test_create_edit_serialize_and_render_vinted_urls(self):
        from app.models import Shirt

        response = self.client.post(
            '/admin/new',
            data=self.product_form(
                vinted_uk_url=' https://www.vinted.co.uk/items/123 ',
                vinted_eu_url='https://www.vinted.it/items/456',
            ),
        )
        self.assertEqual(response.status_code, 302)

        with self.app.app_context():
            shirt = Shirt.query.one()
            self.assertEqual(shirt.vinted_uk_url, 'https://www.vinted.co.uk/items/123')
            self.assertEqual(shirt.vinted_eu_url, 'https://www.vinted.it/items/456')
            self.assertEqual(shirt.to_dict()['vinted_uk_url'], shirt.vinted_uk_url)
            shirt_id = shirt.id
            slug = shirt.slug

        detail = self.client.get(f'/shirt/{shirt_id}-{slug}', follow_redirects=True)
        self.assertEqual(detail.status_code, 200)
        self.assertIn(b'Vinted UK', detail.data)
        self.assertIn(b'Vinted EU', detail.data)
        self.assertIn(b'target="_blank"', detail.data)
        self.assertIn(b'images/vinted-logo.svg', detail.data)

        response = self.client.post(
            f'/admin/edit/{shirt_id}',
            data=self.product_form(
                vinted_uk_url='',
                vinted_eu_url='https://www.vinted.fr/items/789',
            ),
        )
        self.assertEqual(response.status_code, 302)

        with self.app.app_context():
            shirt = self.db.session.get(Shirt, shirt_id)
            self.assertIsNone(shirt.vinted_uk_url)
            self.assertEqual(shirt.vinted_eu_url, 'https://www.vinted.fr/items/789')

        detail = self.client.get(f'/shirt/{shirt_id}-{slug}', follow_redirects=True)
        self.assertNotIn(b'Vinted UK', detail.data)
        self.assertIn(b'Vinted EU', detail.data)

    def test_rejects_non_vinted_url(self):
        from app.models import Shirt

        response = self.client.post(
            '/admin/new',
            data=self.product_form(vinted_uk_url='https://example.com/items/123'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Vinted UK must be a valid Vinted http(s) URL.', response.data)

        with self.app.app_context():
            self.assertEqual(Shirt.query.count(), 0)

    def test_existing_product_without_urls_has_no_buttons(self):
        from app.models import Shirt

        with self.app.app_context():
            shirt = Shirt(
                product_code=1,
                brand='Nike',
                squadra='Italy',
                campionato='National Teams',
                taglia='L',
                colore='Blue',
                stagione='2025-26',
                type='Shirt',
                descrizione='',
                status='active',
            )
            self.db.session.add(shirt)
            self.db.session.commit()
            shirt_id = shirt.id
            slug = shirt.slug

        detail = self.client.get(f'/shirt/{shirt_id}-{slug}', follow_redirects=True)
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn(b'Vinted UK', detail.data)
        self.assertNotIn(b'Vinted EU', detail.data)


if __name__ == '__main__':
    unittest.main()
