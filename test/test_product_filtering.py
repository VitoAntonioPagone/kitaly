import os
import re
import tempfile
import unittest
from html import unescape


class ProductHierarchyFilteringTestCase(unittest.TestCase):
    def setUp(self):
        self.database_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.database_file.close()
        self.upload_dir = tempfile.mkdtemp()

        os.environ['DATABASE_URL'] = f'sqlite:///{self.database_file.name}'
        os.environ['SECRET_KEY'] = 'test-secret'
        os.environ['UPLOAD_FOLDER'] = self.upload_dir

        from app import create_app
        from app.models import Shirt, db

        self.Shirt = Shirt
        self.db = db
        self.app = create_app()
        self.app.config.update(TESTING=True)

        with self.app.app_context():
            self.db.create_all()
            products = [
                self.make_product(1, 'Ac Milan', 'Serie A', 'Lotto', 'Track Jacket', '1995/1996'),
                self.make_product(2, 'Ac Milan', 'Serie A', 'Adidas', 'Tracksuit', '2000/2001'),
                self.make_product(3, 'Inter Milan', 'Serie A', 'Nike', 'Shirt', '1995/1996'),
                self.make_product(4, 'milan', 'Bundesliga', 'Adidas', 'Training Top', '1997/1998'),
                self.make_product(
                    5,
                    'Juventus',
                    'Serie A',
                    'Kappa',
                    'Shirt',
                    '1995/1996',
                    descrizione='A generic description mentioning AC Milan.',
                ),
                self.make_product(
                    6,
                    'Ac Milan',
                    'National Teams',
                    'Puma',
                    'Shirt',
                    '2025/2026',
                    nazionale=True,
                ),
            ]
            self.db.session.add_all(products)
            self.db.session.commit()
            self.target_id = products[0].id

        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            self.db.session.remove()
            self.db.drop_all()
        os.unlink(self.database_file.name)

    def make_product(
        self,
        product_code,
        squadra,
        campionato,
        brand,
        product_type,
        stagione,
        descrizione='',
        nazionale=False,
    ):
        return self.Shirt(
            product_code=product_code,
            brand=brand,
            squadra=squadra,
            campionato=campionato,
            taglia='L',
            colore='Red',
            stagione=stagione,
            type=product_type,
            descrizione=descrizione,
            status='active',
            nazionale=nazionale,
        )

    @staticmethod
    def product_ids(response):
        html = response.get_data(as_text=True)
        return {int(value) for value in re.findall(r'href="/shirt/(\d+)-', html)}

    def test_exact_ac_milan_hierarchy_excludes_partial_and_text_matches(self):
        response = self.client.get(
            '/catalogue',
            query_string={
                'nazionale': '0',
                'campionato': 'Serie A',
                'squadra': 'Ac Milan',
                'sort': 'oldest',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.product_ids(response), {1, 2})
        page = response.get_data(as_text=True)
        self.assertIn('Italian Clubs', page)
        self.assertIn('Serie A', page)
        self.assertIn('Ac Milan', page)
        self.assertIn('type="hidden" name="nazionale" value="0"', page)
        self.assertNotIn('Inter Milan Nike', page)
        self.assertNotIn('milan Adidas', page)
        self.assertNotIn('Juventus Kappa', page)

    def test_team_filter_is_exact_without_full_hierarchy(self):
        response = self.client.get('/catalogue', query_string={'squadra': 'Ac Milan'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.product_ids(response), {1, 2, 6})

    def test_last_boolean_value_controls_preserved_club_filter(self):
        response = self.client.get(
            '/catalogue?nazionale=0&nazionale=1&campionato=National+Teams&squadra=Ac+Milan'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.product_ids(response), {6})

    def test_product_breadcrumb_uses_structured_filters_and_exact_product_link(self):
        with self.app.app_context():
            target = self.db.session.get(self.Shirt, self.target_id)
            detail_url = f'/shirt/{target.id}'

        response = self.client.get(detail_url, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        page = unescape(response.get_data(as_text=True))

        self.assertIn('/catalogue?nazionale=0&campionato=Serie+A&squadra=Ac+Milan', page)
        self.assertNotIn('/catalogue?q=Ac+Milan', page)
        self.assertIn(f'/shirt/{self.target_id}-', page)
        self.assertIn('Ac Milan Lotto Track Jacket 1995/1996', page)
        self.assertNotIn('Inter Milan Nike Shirt', page)


if __name__ == '__main__':
    unittest.main()
