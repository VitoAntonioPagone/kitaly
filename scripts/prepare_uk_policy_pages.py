"""Create the reviewed contact page and private UK policy drafts; never overwrite pages."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import create_app
from app.models import db, StorePage

PAGES = [
    ('contact-us', 'Contact us', 'Contattaci', True),
    ('delivery', 'Delivery', 'Spedizioni', False),
    ('returns-refunds', 'Returns & refunds', 'Resi e rimborsi', False),
    ('terms-conditions', 'Terms & conditions', 'Termini e condizioni', False),
    ('privacy-cookies', 'Privacy & cookies', 'Privacy e cookie', False),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Save pages. Default is a dry run.')
    args = parser.parse_args()
    app = create_app()
    with app.app_context():
        for position, (slug, title_en, title_it, published) in enumerate(PAGES, 10):
            if StorePage.query.filter_by(slug=slug).first():
                print(f'Skip existing page: {slug}')
                continue
            body = (ROOT / 'content' / 'uk-policies' / f'{slug}.txt').read_text().strip()
            if published and ('[CONFIRM:' in body or body.startswith('DRAFT')):
                raise ValueError(f'Cannot publish incomplete page: {slug}')
            db.session.add(StorePage(slug=slug, title_en=title_en, title_it=title_it,
                                     body_en=body, body_it='', published=published,
                                     position=position))
            print(f'{"Create" if args.apply else "Would create"}: {slug} ({"published" if published else "draft"})')
        if args.apply:
            db.session.commit()
        else:
            db.session.rollback()


if __name__ == '__main__':
    main()
