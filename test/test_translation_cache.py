import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from requests.exceptions import HTTPError


class TranslationCacheTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            'DATABASE_URL': 'sqlite:///' + self.directory.name + '/test.db',
            'SECRET_KEY': 'translation-test', 'UPLOAD_FOLDER': self.directory.name + '/uploads',
            'ADMIN_URL_PREFIX': 'admin', 'OPENROUTER_API_KEY': 'test-key', 'OPENROUTER_MODEL': 'test-model',
        })
        self.env.start()
        from app import create_app
        from app.models import db, Shirt
        self.db, self.Shirt = db, Shirt
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.shirt = Shirt(product_code=1, brand='Nike', squadra='Italy', campionato='National Teams',
                           taglia='L', colore='Blue', stagione='1998-99', type='Shirt',
                           descrizione='Original description.', status='active')
        db.session.add(self.shirt)
        db.session.commit()
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session['logged_in'] = True

    def tearDown(self):
        self.db.session.remove()
        self.db.engine.dispose()
        self.ctx.pop()
        self.env.stop()
        self.directory.cleanup()

    def form(self, **changes):
        values = dict(brand='Nike', squadra='Italy', campionato='National Teams', taglia='L',
                      colore='Blue', stagione='1998-99', type='Shirt', descrizione='Original description.', status='active')
        values.update(changes)
        return values

    def test_success_is_saved_and_second_request_reuses_database_cache(self):
        from app.openrouter import get_or_translate_description
        with patch('app.openrouter.translate_to_italian', return_value='Descrizione originale.') as translate:
            self.assertEqual(get_or_translate_description(self.shirt), 'Descrizione originale.')
            self.db.session.expire_all()
            self.assertEqual(get_or_translate_description(self.db.session.get(self.Shirt, 1)), 'Descrizione originale.')
            translate.assert_called_once()
        self.assertEqual(self.db.session.get(self.Shirt, 1).descrizione_ita, 'Descrizione originale.')

    def test_invalid_cache_is_replaced_but_failed_requests_are_not_cached_as_italian(self):
        from app.openrouter import get_or_translate_description
        self.shirt.descrizione_ita = '  None  '
        self.db.session.commit()
        with patch('app.openrouter.translate_to_italian', return_value=None):
            self.assertEqual(get_or_translate_description(self.shirt), 'Original description.')
        with patch('app.openrouter.translate_to_italian', return_value='Descrizione originale.') as translate:
            self.assertEqual(get_or_translate_description(self.shirt), 'Descrizione originale.')
            translate.assert_called_once()

    def test_concurrent_description_edit_is_not_given_stale_translation(self):
        from app.openrouter import get_or_translate_description
        def translate(source):
            self.db.session.query(self.Shirt).filter_by(id=1).update({'descrizione': 'Updated while translating.'})
            self.db.session.commit()
            return 'Traduzione della vecchia descrizione.'
        with patch('app.openrouter.translate_to_italian', side_effect=translate):
            self.assertEqual(get_or_translate_description(self.shirt), 'Updated while translating.')
        self.assertIsNone(self.shirt.descrizione_ita)

    def test_unrelated_admin_save_preserves_cached_translation(self):
        self.shirt.descrizione_ita = 'Descrizione originale.'
        self.db.session.commit()
        with patch('app.openrouter.translate_to_italian') as translate:
            response = self.client.post('/admin/edit/1', data=self.form(condition_rating='9'))
            self.assertEqual(response.status_code, 302)
            translate.assert_not_called()
        self.assertEqual(self.db.session.get(self.Shirt, 1).descrizione_ita, 'Descrizione originale.')

    def test_english_edit_refreshes_old_translation_but_preserves_new_manual_italian(self):
        self.shirt.descrizione_ita = 'Descrizione originale.'
        self.db.session.commit()
        with patch('app.openrouter.translate_to_italian', return_value='Nuova descrizione.') as translate:
            response = self.client.post('/admin/edit/1', data=self.form(
                descrizione='Updated description.', descrizione_ita='Descrizione originale.'))
            self.assertEqual(response.status_code, 302)
            translate.assert_called_once_with('Updated description.')
        self.assertEqual(self.db.session.get(self.Shirt, 1).descrizione_ita, 'Nuova descrizione.')
        with patch('app.openrouter.translate_to_italian') as translate:
            response = self.client.post('/admin/edit/1', data=self.form(
                descrizione='Another description.', descrizione_ita='Traduzione manuale.'))
            self.assertEqual(response.status_code, 302)
            translate.assert_not_called()
        self.assertEqual(self.db.session.get(self.Shirt, 1).descrizione_ita, 'Traduzione manuale.')

    def test_malformed_and_empty_provider_responses_fall_back_without_crashing(self):
        from app.openrouter import translate_to_italian
        for data in [{}, {'choices': []}, {'choices': [{'message': {'content': None}}]},
                     {'choices': [{'message': {'content': '   '}}]}, {'error': {'message': 'Unavailable'}}]:
            response = Mock(status_code=200, json=Mock(return_value=data))
            with patch('app.openrouter.requests.post', return_value=response):
                self.assertIsNone(translate_to_italian('Original description.'))
        response = Mock(status_code=404)
        response.raise_for_status.side_effect = HTTPError('Model unavailable')
        with patch('app.openrouter.requests.post', return_value=response):
            self.assertIsNone(translate_to_italian('Original description.'))


if __name__ == '__main__':
    unittest.main()
