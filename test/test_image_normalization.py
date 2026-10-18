import tempfile
import unittest
from pathlib import Path
from PIL import Image
from app.image_utils import normalize_product_image

class SquareUploadTest(unittest.TestCase):
    def test_square_original_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'square.png'
            Image.new('RGB', (1512, 1512), 'red').save(path)
            original = path.read_bytes()
            self.assertFalse(normalize_product_image(path))
            self.assertEqual(path.read_bytes(), original)

    def test_portrait_upload_becomes_square(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'portrait.jpg'
            Image.new('RGB', (1000, 1500), 'blue').save(path)
            self.assertTrue(normalize_product_image(path))
            with Image.open(path) as image:
                self.assertEqual(image.size, (1512, 1512))

    def test_preserves_edges_of_non_square_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'edges.png'
            original = Image.new('RGB', (100, 200), 'blue')
            for y in range(20):
                for x in range(100):
                    original.putpixel((x, y), (255, 0, 0))
                    original.putpixel((x, 199-y), (0, 255, 0))
            original.save(path)
            normalize_product_image(path)
            with Image.open(path) as image:
                self.assertEqual(image.getpixel((756, 10)), (255, 0, 0))
                self.assertEqual(image.getpixel((756, 1500)), (0, 255, 0))

    def test_square_upload_applies_exif_orientation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'rotated.jpg'
            original = Image.new('RGB', (1512, 1512), 'blue')
            original.paste('red', (0, 0, 1512, 756))
            exif = original.getexif()
            exif[274] = 6
            original.save(path, exif=exif)
            self.assertTrue(normalize_product_image(path))
            with Image.open(path) as image:
                self.assertEqual(image.size, (1512, 1512))
                self.assertEqual(image.getexif().get(274, 1), 1)
                self.assertGreater(image.getpixel((1200, 756))[0], 240)
                self.assertGreater(image.getpixel((300, 756))[2], 240)
            self.assertFalse(normalize_product_image(path))
