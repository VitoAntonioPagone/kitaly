"""Populate missing Italian description caches without replacing existing translations."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db, Shirt
from app.openrouter import get_or_translate_description, normalize_translation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--active-only', action='store_true')
    args = parser.parse_args()
    app = create_app()
    with app.app_context():
        query = Shirt.query.order_by(Shirt.id)
        if args.active_only:
            query = query.filter_by(status='active')
        pending = [shirt.id for shirt in query.all()
                   if shirt.descrizione and shirt.descrizione.strip() and not normalize_translation(shirt.descrizione_ita)]
        print(f'Missing Italian descriptions: {len(pending)}', flush=True)
        failed = []
        for index, shirt_id in enumerate(pending, 1):
            shirt = db.session.get(Shirt, shirt_id)
            get_or_translate_description(shirt)
            cached = bool(normalize_translation(shirt.descrizione_ita))
            if not cached:
                failed.append(shirt_id)
            print(f'{index}/{len(pending)} shirt={shirt_id} cached={cached}', flush=True)
        print(f'Cached {len(pending) - len(failed)}/{len(pending)} descriptions; remaining IDs: {failed}', flush=True)
        return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
