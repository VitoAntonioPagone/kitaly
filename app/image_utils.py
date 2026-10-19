import os
from pathlib import Path

from PIL import Image, ImageOps


PRODUCT_IMAGE_SIZE = (1512, 1512)
PRODUCT_IMAGE_RATIO = PRODUCT_IMAGE_SIZE[0] / PRODUCT_IMAGE_SIZE[1]


def _flatten_transparency(image):
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        base = Image.new("RGB", image.size, (255, 255, 255))
        base.paste(image.convert("RGBA"), mask=image.convert("RGBA").split()[-1])
        return base
    return image.convert("RGB") if image.mode not in ("RGB", "L") else image


def normalize_product_image(path, size=PRODUCT_IMAGE_SIZE):
    image_path = Path(path)
    if not image_path.exists() or not image_path.is_file():
        return False

    with Image.open(image_path) as image:
        orientation = image.getexif().get(274, 1)
        image = ImageOps.exif_transpose(image)
        if image.size == size and orientation == 1:
            return False

        image = _flatten_transparency(image)
        image = ImageOps.pad(image, size, method=Image.Resampling.LANCZOS, color="white", centering=(0.5, 0.5))

        suffix = image_path.suffix.lower()
        save_kwargs = {}
        if suffix in {".jpg", ".jpeg"}:
            save_kwargs = {"quality": 92, "optimize": True, "progressive": True}
        elif suffix == ".png":
            save_kwargs = {"optimize": True}
        elif suffix == ".webp":
            save_kwargs = {"quality": 92, "method": 6}

        temp_path = image_path.with_name(f"{image_path.stem}.normalized{image_path.suffix}")
        image.save(temp_path, **save_kwargs)
        os.replace(temp_path, image_path)

    return True


# Browser-sized derivatives leave the uploaded originals untouched.
IMAGE_VARIANTS = {'thumb': (160, 78), 'card': (640, 82), 'detail': (1280, 86)}


def product_image_source(upload_root, filename):
    root = Path(upload_root).resolve()
    source = (root / filename).resolve()
    if root not in source.parents or '.previews' in source.relative_to(root).parts:
        raise ValueError('Invalid image path')
    if not source.is_file():
        raise FileNotFoundError(filename)
    return source


def product_image_version(source):
    stat = source.stat()
    return f'{stat.st_mtime_ns:x}-{stat.st_size:x}'


def product_image_preview(upload_root, filename, variant):
    import hashlib
    import tempfile
    if variant not in IMAGE_VARIANTS:
        raise ValueError('Unknown image size')
    source = product_image_source(upload_root, filename)
    key = hashlib.sha256((str(source) + product_image_version(source)).encode()).hexdigest()
    folder = Path(upload_root) / '.previews' / variant
    destination = folder / (key + '.webp')
    if destination.is_file():
        return destination
    folder.mkdir(parents=True, exist_ok=True)
    width, quality = IMAGE_VARIANTS[variant]
    with Image.open(source) as original:
        image = _flatten_transparency(ImageOps.exif_transpose(original))
        image.thumbnail((width, width), Image.Resampling.LANCZOS)
        with tempfile.NamedTemporaryFile(dir=folder, suffix='.webp', delete=False) as temporary:
            temporary_path = Path(temporary.name)
        try:
            image.save(temporary_path, format='WEBP', quality=quality, method=4)
            temporary_path.chmod(0o644)
            os.replace(temporary_path, destination)
        finally:
            temporary_path.unlink(missing_ok=True)
    return destination


def prepare_product_previews(upload_root, filename):
    for variant in IMAGE_VARIANTS:
        product_image_preview(upload_root, filename, variant)
