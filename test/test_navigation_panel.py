import os
import tempfile
import unittest
from html.parser import HTMLParser
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit


class MenuLinks(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.inside = False
        self.current = None
        self.links = {}
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'dialog' and attrs.get('id') == 'mobile-menu':
            self.inside = True
        if self.inside and tag == 'a':
            self.current = (attrs, [])

    def handle_data(self, data):
        if self.current:
            self.current[1].append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self.current:
            attrs, parts = self.current
            self.links.setdefault(' '.join(''.join(parts).split()), attrs)
            self.current = None
        if tag == 'dialog':
            self.inside = False


class NavigationPanelTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            'DATABASE_URL': 'sqlite:///' + self.directory.name + '/test.db',
            'SECRET_KEY': 'navigation-test',
            'UPLOAD_FOLDER': self.directory.name + '/uploads',
        })
        self.env.start()
        from app import create_app
        from app.models import db
        self.app = create_app()
        self.db = db
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            self.db.session.remove()
            self.db.engine.dispose()
        self.env.stop()
        self.directory.cleanup()

    def menu(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return MenuLinks(response.get_data(as_text=True)).links

    def test_collections_use_live_catalogue_filters(self):
        links = self.menu('/catalogue')
        self.assertEqual(links['All stock'].get('aria-current'), 'page')
        for league in ['Serie A', 'Premier League', 'La Liga', 'Bundesliga', 'Ligue 1']:
            target = urlsplit(links[league]['href'])
            self.assertEqual(target.path, '/catalogue')
            self.assertEqual(parse_qs(target.query), {'campionato': [league]})
        self.assertEqual(parse_qs(urlsplit(links['Player Issue']['href']).query), {'player_issued': ['1']})
        self.assertEqual(parse_qs(urlsplit(links['National teams']['href']).query), {'nazionale': ['1']})

    def test_selected_collection_and_language_survive_navigation(self):
        links = self.menu('/catalogue?campionato=Serie+A&lang=it')
        self.assertEqual(links['Serie A'].get('aria-current'), 'page')
        self.assertNotIn('aria-current', links['Tutto lo stock'])
        self.assertEqual(links['Italiano'].get('aria-current'), 'true')
        query = parse_qs(urlsplit(links['English']['href']).query)
        self.assertEqual(query['campionato'], ['Serie A'])
        self.assertEqual(query['lang'], ['en'])

    def test_curated_selection_clears_league_highlight(self):
        links = self.menu('/catalogue?player_issued=1')
        self.assertEqual(links['Player Issue'].get('aria-current'), 'page')
        self.assertNotIn('aria-current', links['All stock'])
        self.assertNotIn('aria-current', links['Serie A'])
