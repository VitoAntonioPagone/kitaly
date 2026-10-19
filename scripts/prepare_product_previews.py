"""Pre-generate browser image variants without modifying uploaded originals."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import ShirtImage
from app.image_utils import prepare_product_previews, product_image_preview


def main():
    app = create_app()
    with app.app_context():
        root = app.config['UPLOAD_FOLDER']
        filenames = [row[0] for row in ShirtImage.query.with_entities(ShirtImage.file_path).distinct().all()]
        total_original = total_cards = 0
        for index, filename in enumerate(filenames, 1):
            prepare_product_previews(root, filename)
            total_original += (Path(root) / filename).stat().st_size
            total_cards += product_image_preview(root, filename, 'card').stat().st_size
            if index % 20 == 0:
                print(f'Prepared {index}/{len(filenames)} product photos', flush=True)
        print(f'Prepared {len(filenames)} photos. Original bytes: {total_original}; catalogue bytes: {total_cards}.', flush=True)


if __name__ == '__main__':
    main()
