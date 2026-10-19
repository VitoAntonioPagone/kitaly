import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse


class AdminPreferencesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            'DATABASE_URL': 'sqlite:///' + self.directory.name + '/test.db',
            'SECRET_KEY': 'test-preferences', 'UPLOAD_FOLDER': self.directory.name + '/uploads',
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
            for code, status in enumerate(['draft', 'draft', 'active'], 1):
                db.session.add(Shirt(product_code=code, brand='Nike', squadra='Italy',
                                     campionato='National Teams', taglia='L', colore='Blue',
                                     stagione='1998-99', type='Shirt', status=status))
            db.session.commit()
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session['logged_in'] = True

    def tearDown(self):
        with self.app.app_context():
            self.db.session.remove()
            self.db.engine.dispose()
        self.env.stop()
        self.directory.cleanup()

    def test_filters_survive_deletion_and_navigation_until_reset(self):
        self.client.get('/admin/?status_filter=draft&brand=Nike&sort=newest')
        response = self.client.post('/admin/delete/1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request.args['status_filter'], 'draft')
        self.assertEqual(response.request.args['brand'], 'Nike')
        self.assertEqual(response.request.args['sort'], 'newest')
        with self.client.session_transaction() as session:
            self.assertEqual(session['dashboard_filters']['status_filter'], 'draft')
        self.client.get('/admin/new')
        self.assertEqual(self.client.get('/admin/').status_code, 302)
        response = self.client.get('/admin/?reset=1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.request.args)
        with self.client.session_transaction() as session:
            self.assertNotIn('dashboard_filters', session)
        self.assertEqual(self.client.get('/admin/').status_code, 200)

    def test_clearing_filters_and_separate_sessions(self):
        self.client.get('/admin/?status_filter=draft&brand=Nike')
        self.client.get('/admin/?status_filter=&brand=&sort=chronological')
        saved = parse_qs(urlparse(self.client.get('/admin/').location).query)
        self.assertNotIn('status_filter', saved)
        self.assertNotIn('brand', saved)
        other = self.app.test_client()
        with other.session_transaction() as session:
            session['logged_in'] = True
        self.assertEqual(other.get('/admin/').status_code, 200)

    def test_team_search_partial_case_insensitive_and_persistent(self):
        with self.app.app_context():
            self.db.session.get(self.Shirt, 3).squadra = 'Arsenal'
            self.db.session.commit()
        response = self.client.get('/admin/?squadra=ITAL&status_filter=draft')
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="team-search" type="search"', page)
        self.assertIn('value="ITAL"', page)
        self.assertIn('Managing 2 archived masterpieces', page)
        saved = parse_qs(urlparse(self.client.get('/admin/').location).query)
        self.assertEqual(saved['squadra'], ['ITAL'])
        response = self.client.post('/admin/delete/1', follow_redirects=True)
        self.assertEqual(response.request.args['squadra'], 'ITAL')
        self.assertIn('Managing 1 archived masterpieces', response.get_data(as_text=True))
        page = self.client.get('/admin/?squadra=NoSuchTeam').get_data(as_text=True)
        self.assertIn('Managing 0 archived masterpieces', page)
        response = self.client.get('/admin/?reset=1', follow_redirects=True)
        self.assertNotIn('squadra', response.request.args)

    def test_new_price_defaults_and_existing_currencies(self):
        from app.blueprints.admin import parse_price_currency
        self.assertEqual(parse_price_currency(None), 'GBP')
        page = self.client.get('/admin/new').get_data(as_text=True)
        self.assertIn('value="GBP" selected', page)
        with self.app.app_context():
            shirt = self.db.session.get(self.Shirt, 1)
            self.assertEqual(shirt.price_currency, 'GBP')
            shirt.price_currency = 'EUR'
            self.db.session.commit()
        page = self.client.get('/admin/edit/1').get_data(as_text=True)
        self.assertIn('value="EUR" selected', page)

    def test_simplified_form_and_legacy_link_preservation(self):
        with self.app.app_context():
            shirt = self.db.session.get(self.Shirt, 1)
            shirt.vinted_uk_url = 'https://www.vinted.co.uk/items/123'
            self.db.session.commit()
        page = self.client.get('/admin/edit/1').get_data(as_text=True)
        self.assertNotIn('name="vinted_', page)
        self.assertNotIn('national-teams-list', page)
        self.assertNotIn('value="Cile"', page)
        self.assertIn('autocomplete="off"', page)
        self.client.post('/admin/edit/1', data={
            'brand': 'Nike', 'squadra': 'Italy', 'campionato': 'National Teams',
            'taglia': 'L', 'colore': 'Blue', 'stagione': '1998-99', 'type': 'Shirt',
            'descrizione': '', 'status': 'draft',
        })
        with self.app.app_context():
            self.assertEqual(self.db.session.get(self.Shirt, 1).vinted_uk_url,
                             'https://www.vinted.co.uk/items/123')

    def test_player_issue_copy_and_compact_card(self):
        with self.app.app_context():
            self.db.session.get(self.Shirt, 3).player_issued = True
            self.db.session.commit()
        copy = Path('templates/components/player_issue_description.html').read_text().strip()
        for route in ['/catalogue', '/shirt/3', '/admin/new']:
            page = self.client.get(route, follow_redirects=True).get_data(as_text=True)
            self.assertIn(copy, page)
        page = self.client.get('/catalogue').get_data(as_text=True)
        self.assertIn('class="catalogue-star-button"', page)
        self.assertNotIn('class="player-issue-label"', page)
        self.assertIn('class="catalogue-size">Size: L', page)
        self.assertNotIn('class="player-issue-badge', page)
