import os
from pathlib import Path

from PIL import Image, ImageOps


PRODUCT_IMAGE_SIZE = (1000, 1500)
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
        image = ImageOps.exif_transpose(image)
        if image.size == size:
            return False

        image = _flatten_transparency(image)
        image = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))

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
