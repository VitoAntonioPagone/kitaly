import os
import tempfile
import unittest
from unittest.mock import patch
from importlib.util import spec_from_file_location, module_from_spec


class StorePagesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            'DATABASE_URL': 'sqlite:///' + self.directory.name + '/test.db',
            'SECRET_KEY': 'pages-test', 'UPLOAD_FOLDER': self.directory.name + '/uploads',
            'ADMIN_URL_PREFIX': 'admin'})
        self.env.start()
        from app import create_app
        from app.models import db, StorePage
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.db, self.Page = db, StorePage
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        with self.client.session_transaction() as s:
            s['logged_in'] = True

    def tearDown(self):
        with self.app.app_context():
            self.db.session.remove()
            self.db.engine.dispose()
        self.env.stop()
        self.directory.cleanup()

    def form(self, **changes):
        result = dict(slug='about', title_en='About Kitaly', title_it='Chi siamo',
                      body_en='English content.\n\nSecond paragraph.', body_it='Contenuto italiano.', position='2')
        result.update(changes)
        return result

    def test_draft_publish_translations_and_unpublish(self):
        self.assertEqual(self.client.get('/admin/pages/new').status_code, 200)
        self.assertEqual(self.client.post('/admin/pages/new', data=self.form()).status_code, 302)
        self.assertEqual(self.client.get('/pages/about').status_code, 404)
        self.assertNotIn('href="/pages/about"', self.client.get('/catalogue').get_data(as_text=True))
        with self.app.app_context():
            page_id = self.Page.query.one().id
        edit = f'/admin/pages/{page_id}/edit'
        self.assertEqual(self.client.post(edit, data=self.form(published='1')).status_code, 302)
        self.assertIn('English content.', self.client.get('/pages/about?lang=en').get_data(as_text=True))
        page = self.client.get('/pages/about?lang=it').get_data(as_text=True)
        self.assertIn('Contenuto italiano.', page)
        self.assertIn('Chi siamo', page)
        self.assertIn('href="/pages/about"', self.client.get('/catalogue').get_data(as_text=True))
        self.assertEqual(self.client.post(edit, data=self.form()).status_code, 302)
        self.assertEqual(self.client.get('/pages/about').status_code, 404)

    def test_validation_escaping_fallback_and_permissions(self):
        for changes in [dict(slug='../bad'), dict(position='x'), dict(position='10000'), dict(published='1', body_en='')]:
            self.assertEqual(self.client.post('/admin/pages/new', data=self.form(**changes)).status_code, 200)
        with self.app.app_context():
            self.assertEqual(self.Page.query.count(), 0)
        content = '<script>alert("test")</script>'
        self.client.post('/admin/pages/new', data=self.form(body_en=content, body_it='', published='1'))
        page = self.client.get('/pages/about?lang=it').get_data(as_text=True)
        self.assertIn('&lt;script&gt;', page)
        self.assertNotIn(content, page)
        response = self.client.post('/admin/pages/new', data=self.form())
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertEqual(self.Page.query.count(), 1)
        self.assertEqual(self.client.get('/admin/pages/999/edit').status_code, 404)
        with self.client.session_transaction() as s:
            s.clear()
        self.assertEqual(self.client.get('/admin/pages').status_code, 302)
        self.assertEqual(self.client.post('/admin/pages/new', data=self.form()).status_code, 302)

    def test_footer_lists_only_published_pages_in_order(self):
        self.client.post('/admin/pages/new', data=self.form(published='1', position='2'))
        self.client.post('/admin/pages/new', data=self.form(slug='shipping', title_en='Shipping', published='1', position='1'))
        page = self.client.get('/catalogue?lang=en').get_data(as_text=True)
        self.client.post('/admin/pages/new', data=self.form(slug='private', title_en='Private draft'))
        self.assertIn('href="/pages/shipping"', page)
        self.assertIn('href="/pages/about"', page)
        self.assertNotIn('href="/pages/private"', self.client.get('/catalogue').get_data(as_text=True))
        self.assertLess(page.index('href="/pages/shipping"'), page.index('href="/pages/about"'))
        with self.app.app_context():
            self.assertEqual(self.Page.query.filter_by(published=True).count(), 2)

    def test_migration_creates_only_draft_pages(self):
        from sqlalchemy import create_engine, text, inspect
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        spec = spec_from_file_location('pages_migration', 'migrations/versions/e82c4319a670_add_store_pages.py')
        migration = module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine('sqlite://')
        with engine.begin() as connection:
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
                rows = connection.execute(text('SELECT slug, published FROM store_pages ORDER BY position')).all()
                self.assertEqual([r[0] for r in rows], ['about', 'shipping', 'authenticity'])
                self.assertTrue(all(not r[1] for r in rows))
                migration.downgrade()
                self.assertNotIn('store_pages', inspect(connection).get_table_names())
        engine.dispose()

    def test_private_preview_and_incomplete_policy_guard(self):
        self.client.post('/admin/pages/new', data=self.form(body_en='DRAFT\n[CONFIRM: legal name]'))
        with self.app.app_context():
            page_id = self.Page.query.one().id
        preview = f'/admin/pages/{page_id}/preview'
        response = self.client.get(preview)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Private draft', response.get_data(as_text=True))
        self.assertEqual(response.headers['X-Robots-Tag'], 'noindex, nofollow')
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.client.post(f'/admin/pages/{page_id}/edit', data=self.form(body_en='[CONFIRM: legal name]', published='1'))
        self.assertEqual(self.client.get('/pages/about').status_code, 404)
        with self.client.session_transaction() as session:
            session.clear()
        self.assertEqual(self.client.get(preview).status_code, 302)

    def test_cookie_preferences_preserve_essential_session_and_stop_language_storage(self):
        self.client.get('/catalogue?lang=it')
        response = self.client.get('/cookie-preferences')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        with self.client.session_transaction() as session:
            token = session['preferences_csrf']
            session['payment_orders'] = ['owned-order']
        self.assertEqual(self.client.post('/cookie-preferences', data={'appearance_preferences': 'off'}).status_code, 400)
        response = self.client.post('/cookie-preferences', data={'csrf_token': token, 'appearance_preferences': 'off'})
        self.assertEqual(response.status_code, 303)
        self.assertIn('appearance_preferences=v1:off', response.headers.getlist('Set-Cookie')[0])
        self.assertIn('Max-Age=15552000', response.headers.getlist('Set-Cookie')[0])
        self.assertIn('SameSite=Lax', response.headers.getlist('Set-Cookie')[0])
        with self.client.session_transaction() as session:
            self.assertNotIn('lang', session)
            self.assertEqual(session['payment_orders'], ['owned-order'])
        self.client.get('/catalogue?lang=it')
        with self.client.session_transaction() as session:
            self.assertNotIn('lang', session)
        self.client.post('/cookie-preferences', data={'csrf_token': token, 'appearance_preferences': 'on'})
        self.client.get('/catalogue?lang=it')
        with self.client.session_transaction() as session:
            self.assertEqual(session['lang'], 'it')

    def test_no_language_storage_before_explicit_consent(self):
        self.client.get('/catalogue?lang=it')
        with self.client.session_transaction() as session:
            self.assertNotIn('lang', session)
        self.client.set_cookie('appearance_preferences', 'on')
        self.client.get('/catalogue?lang=it')
        with self.client.session_transaction() as session:
            self.assertNotIn('lang', session)
        self.client.set_cookie('appearance_preferences', 'v1:on')
        self.client.get('/catalogue?lang=it')
        with self.client.session_transaction() as session:
            self.assertEqual(session['lang'], 'it')

    def test_mobile_menu_player_issue_shirts_pool(self):
        import html
        import json
        import re
        from app.models import Shirt, ShirtImage

        with self.app.app_context():
            pi_one = Shirt(
                product_code=1001, brand='Kappa', squadra='Roma', campionato='Serie A',
                taglia='L', colore='Red', stagione='2000-01', player_issued=True,
                sold=False, status='active'
            )
            pi_one.images.append(ShirtImage(file_path='pi-one.jpg', is_cover=True))
            pi_two = Shirt(
                product_code=1002, brand='Nike', squadra='Inter', campionato='Serie A',
                taglia='M', colore='Blue', stagione='2009-10', player_issued=True,
                sold=False, status='active'
            )
            pi_two.images.append(ShirtImage(file_path='pi-two.jpg', is_cover=True))
            sold_pi = Shirt(
                product_code=1003, brand='Adidas', squadra='Milan', campionato='Serie A',
                taglia='L', colore='Red', stagione='1998-99', player_issued=True,
                sold=True, status='active'
            )
            sold_pi.images.append(ShirtImage(file_path='sold-pi.jpg', is_cover=True))
            regular = Shirt(
                product_code=1004, brand='Lotto', squadra='Juve', campionato='Serie A',
                taglia='L', colore='Black', stagione='1997-98', player_issued=False,
                sold=False, status='active'
            )
            regular.images.append(ShirtImage(file_path='regular.jpg', is_cover=True))
            self.db.session.add_all([pi_one, pi_two, sold_pi, regular])
            self.db.session.commit()

        response = self.client.get('/catalogue')
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        match = re.search(r'data-player-issue-shirts="([^"]*)"', body)
        self.assertIsNotNone(match)
        pool = json.loads(html.unescape(match.group(1)))
        srcs = [item['src'] for item in pool]
        self.assertEqual(len(pool), 2)
        self.assertTrue(any('pi-one.jpg' in src for src in srcs))
        self.assertTrue(any('pi-two.jpg' in src for src in srcs))
        self.assertFalse(any('sold-pi.jpg' in src for src in srcs))
        self.assertFalse(any('regular.jpg' in src for src in srcs))
