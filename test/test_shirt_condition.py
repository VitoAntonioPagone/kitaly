import importlib.util
import os
import tempfile
import unittest
from unittest.mock import patch


class ShirtConditionTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            'DATABASE_URL': 'sqlite:///' + self.directory.name + '/test.db',
            'SECRET_KEY': 'condition-test', 'UPLOAD_FOLDER': self.directory.name + '/uploads',
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
        self.directory.cleanup()

    def form(self, **changes):
        values = dict(brand='Nike', squadra='Italy', campionato='National Teams', taglia='L',
                      colore='Blue', stagione='1998-99', type='Shirt', descrizione='', status='active',
                      condition_rating='8', condition_notes='Light wear to the sponsor print.')
        values.update(changes)
        return values

    def test_create_edit_and_condition_only_on_detail(self):
        response = self.client.post('/admin/new', data=self.form())
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            shirt = self.Shirt.query.one()
            self.assertEqual(shirt.condition_rating, 8)
            self.assertEqual(shirt.to_dict()['condition_notes'], 'Light wear to the sponsor print.')
            shirt_id = shirt.id
        detail = self.client.get(f'/shirt/{shirt_id}', follow_redirects=True).get_data(as_text=True)
        self.assertIn('>8/10</p>', detail)
        self.assertIn('Light wear to the sponsor print.', detail)
        catalogue = self.client.get('/catalogue').get_data(as_text=True)
        self.assertNotIn('8/10', catalogue)
        self.assertNotIn('Light wear to the sponsor print.', catalogue)
        self.assertNotIn('shirt-condition', catalogue)
        edit = self.client.get(f'/admin/edit/{shirt_id}').get_data(as_text=True)
        self.assertIn('value="8"', edit)
        self.assertIn('Light wear to the sponsor print.', edit)
        response = self.client.post(f'/admin/edit/{shirt_id}', data=self.form(condition_rating='10', condition_notes='  '))
        self.assertEqual(response.status_code, 302)
        detail = self.client.get(f'/shirt/{shirt_id}', follow_redirects=True).get_data(as_text=True)
        self.assertIn('>10/10</p>', detail)
        self.assertNotIn('class="shirt-condition-notes"', detail)
        self.client.post(f'/admin/edit/{shirt_id}', data=self.form(condition_rating='', condition_notes=''))
        detail = self.client.get(f'/shirt/{shirt_id}', follow_redirects=True).get_data(as_text=True)
        self.assertNotIn('class="shirt-condition"', detail)

    def test_optional_notes_are_escaped_and_can_exist_without_rating(self):
        self.client.post('/admin/new', data=self.form(condition_rating='', condition_notes='  <script>alert(1)</script>  '))
        detail = self.client.get('/shirt/1', follow_redirects=True).get_data(as_text=True)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', detail)
        self.assertNotIn('class="shirt-condition-rating"', detail)
        self.assertNotIn('<script>alert(1)</script>', detail)

    def test_invalid_scores_and_long_notes_do_not_create_records(self):
        for value in ['0', '11', '-1', '8.5', 'abc', 'NaN', '1e1']:
            with self.subTest(value=value):
                response = self.client.post('/admin/new', data=self.form(condition_rating=value))
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Condition must be a whole number from 1 to 10.', response.data)
        response = self.client.post('/admin/new', data=self.form(condition_notes='x' * 2001))
        self.assertIn(b'Condition notes must be 2,000 characters or fewer.', response.data)
        with self.app.app_context():
            self.assertEqual(self.Shirt.query.count(), 0)

    def test_invalid_edit_is_atomic_and_omitted_fields_are_preserved(self):
        self.client.post('/admin/new', data=self.form(condition_rating='1'))
        response = self.client.post('/admin/edit/1', data=self.form(condition_rating='9', condition_notes='x' * 2001, brand='Changed'))
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            shirt = self.db.session.get(self.Shirt, 1)
            self.assertEqual(shirt.condition_rating, 1)
            self.assertEqual(shirt.brand, 'Nike')
        legacy = self.form()
        legacy.pop('condition_rating')
        legacy.pop('condition_notes')
        self.client.post('/admin/edit/1', data=legacy)
        with self.app.app_context():
            self.assertEqual(self.db.session.get(self.Shirt, 1).condition_rating, 1)

    def test_new_fields_are_optional_and_admin_only(self):
        page = self.client.get('/admin/new').get_data(as_text=True)
        self.assertIn('name="condition_rating" min="1" max="10" step="1"', page)
        self.assertIn('name="condition_notes" rows="3" maxlength="2000"', page)
        self.client.post('/admin/new', data=self.form(condition_rating='', condition_notes=''))
        with self.app.app_context():
            self.assertIsNone(self.Shirt.query.one().condition_rating)
            self.assertIsNone(self.Shirt.query.one().condition_notes)
        anonymous = self.app.test_client()
        self.assertEqual(anonymous.get('/admin/new').status_code, 302)


class ConditionMigrationTest(unittest.TestCase):
    def test_upgrade_and_downgrade_preserve_existing_records(self):
        import sqlalchemy as sa
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        spec = importlib.util.spec_from_file_location('condition_migration', 'migrations/versions/d24a9b73c861_add_shirt_condition.py')
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = sa.create_engine('sqlite://')
        with engine.begin() as connection:
            connection.execute(sa.text('CREATE TABLE shirts (id INTEGER PRIMARY KEY, price_currency VARCHAR(3))'))
            connection.execute(sa.text("INSERT INTO shirts VALUES (1, 'EUR')"))
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
            row = connection.execute(sa.text('SELECT * FROM shirts')).mappings().one()
            self.assertEqual(row['price_currency'], 'EUR')
            self.assertIsNone(row['condition_rating'])
            self.assertIsNone(row['condition_notes'])
            with self.assertRaises(sa.exc.IntegrityError):
                connection.execute(sa.text('UPDATE shirts SET condition_rating=11'))
            connection.execute(sa.text("UPDATE shirts SET condition_rating=8, condition_notes='Good condition'"))
            with Operations.context(MigrationContext.configure(connection)):
                migration.downgrade()
            self.assertEqual(connection.execute(sa.text('SELECT * FROM shirts')).one(), (1, 'EUR'))
        engine.dispose()
