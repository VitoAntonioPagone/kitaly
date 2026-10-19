import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from io import BytesIO
from PIL import Image


class ProductImageDeliveryTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.env = patch.dict(os.environ, {'DATABASE_URL': 'sqlite:///' + str(self.root/'test.db'),
            'SECRET_KEY': 'images-test', 'UPLOAD_FOLDER': str(self.root/'uploads'), 'ADMIN_URL_PREFIX': 'admin'})
        self.env.start()
        from app import create_app
        from app.models import db, Shirt, ShirtImage
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.db = db
        self.source = self.root/'uploads'/'photo.jpg'
        Image.effect_noise((1512, 1512), 40).convert('RGB').save(self.source, quality=95)
        with self.app.app_context():
            db.create_all()
            shirt = Shirt(product_code=1, brand='Nike', squadra='Italy', campionato='', taglia='L',
                          colore='Blue', stagione='1998-99', status='active')
            db.session.add(shirt)
            db.session.flush()
            db.session.add_all([ShirtImage(shirt_id=shirt.id, file_path='photo.jpg', is_cover=True),
                                ShirtImage(shirt_id=shirt.id, file_path='other.jpg')])
            db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            self.db.session.remove()
            self.db.engine.dispose()
        self.env.stop()
        self.directory.cleanup()

    def test_variants_are_small_cached_and_preserve_original(self):
        from app.image_utils import product_image_preview, product_image_version
        original = self.source.read_bytes()
        for variant, width in [('thumb',160),('card',640),('detail',1280)]:
            with self.subTest(variant=variant):
                version = product_image_version(self.source)
                response = self.client.get(f'/media/{variant}/photo.jpg?v={version}')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, 'image/webp')
                self.assertIn('immutable', response.headers['Cache-Control'])
                with Image.open(BytesIO(response.data)) as image:
                    self.assertEqual(image.size, (width,width))
                self.assertLess(len(response.data),len(original))
                target = product_image_preview(self.source.parent,'photo.jpg',variant)
                timestamp = target.stat().st_mtime_ns
                product_image_preview(self.source.parent,'photo.jpg',variant)
                self.assertEqual(timestamp,target.stat().st_mtime_ns)
                cached = self.client.get(f'/media/{variant}/photo.jpg?v={version}',headers={'If-None-Match':response.headers['ETag']})
                self.assertEqual(cached.status_code,304)
                cached.close()
                response.close()
        self.assertEqual(original,self.source.read_bytes())

    def test_replaced_photos_get_new_url_and_unsafe_paths_are_rejected(self):
        from app.image_utils import product_image_preview, product_image_version
        version = product_image_version(self.source)
        first = product_image_preview(self.source.parent,'photo.jpg','card')
        Image.new('RGB',(500,500),'red').save(self.source)
        self.assertNotEqual(version,product_image_version(self.source))
        self.assertNotEqual(first,product_image_preview(self.source.parent,'photo.jpg','card'))
        for url in ['/media/huge/photo.jpg','/media/card/missing.jpg','/media/card/../test.db','/media/card/.previews/card/private.webp']:
            self.assertEqual(self.client.get(url).status_code,404)

    def test_new_uploads_prepare_all_sizes_before_first_visit(self):
        from app.models import ShirtImage
        from app.image_utils import IMAGE_VARIANTS
        with self.client.session_transaction() as session:
            session['logged_in'] = True
        response = self.client.post('/admin/new', data={
            'brand':'Adidas','squadra':'Arsenal','campionato':'','taglia':'L',
            'colore':'Red','stagione':'2000-01','type':'Shirt','status':'active',
            'images':(BytesIO(self.source.read_bytes()),'new.jpg')})
        self.assertEqual(response.status_code,302)
        with self.app.app_context():
            uploaded = ShirtImage.query.order_by(ShirtImage.id.desc()).first()
            self.assertNotEqual(uploaded.file_path,'other.jpg')
        for variant in IMAGE_VARIANTS:
            self.assertTrue(list((self.source.parent/'.previews'/variant).glob('*.webp')))

    def test_visible_cover_is_prioritized_and_hidden_images_do_not_compete(self):
        import re
        page = self.client.get('/catalogue').get_data(as_text=True)
        images = re.findall(r'<img[^>]*data-gallery-image[^>]*>',page)
        self.assertEqual(len(images),2)
        self.assertIn('loading="eager"',images[0])
        self.assertIn('fetchpriority="high"',images[0])
        self.assertIn('/media/card/',images[0])
        self.assertIn('data-src=',images[1])
        self.assertNotRegex(images[1], r'(?<!data-)\bsrc=')
        page = self.client.get('/shirt/1',follow_redirects=True).get_data(as_text=True)
        self.assertIn('rel="preload" as="image"',page)
        self.assertIn('/media/detail/',page)
        self.assertIn('/media/thumb/',page)
