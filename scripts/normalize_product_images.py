#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.image_utils import PRODUCT_IMAGE_SIZE, normalize_product_image


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def iter_images(upload_dir):
    for path in upload_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            yield path


def main():
    parser = argparse.ArgumentParser(
        description=f"Normalize product photos to {PRODUCT_IMAGE_SIZE[0]}x{PRODUCT_IMAGE_SIZE[1]}."
    )
    parser.add_argument("upload_dir", nargs="?", default="uploads", help="Upload directory to scan.")
    parser.add_argument("--dry-run", action="store_true", help="List images without changing them.")
    args = parser.parse_args()

    upload_dir = Path(args.upload_dir).resolve()
    if not upload_dir.exists():
        raise SystemExit(f"Upload directory not found: {upload_dir}")

    total = 0
    changed = 0
    failed = 0
    for image_path in iter_images(upload_dir):
        total += 1
        if args.dry_run:
            print(image_path)
            continue
        try:
            if normalize_product_image(image_path):
                changed += 1
                print(f"normalized {image_path}")
        except Exception as exc:
            failed += 1
            print(f"failed {image_path}: {exc}")

    if args.dry_run:
        print(f"found {total} image(s) in {upload_dir}")
    else:
        print(f"normalized {changed}/{total} image(s); failed {failed}")
        if failed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
