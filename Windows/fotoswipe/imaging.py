from pathlib import Path
from PIL import Image, ImageOps
from .core import PhotoError, snapshot

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass


def preview(path, maximum=(1800, 1400)):
    with Image.open(path) as image:
        image.seek(0)
        image.draft('RGB', maximum)
        image = ImageOps.exif_transpose(image)
        image.thumbnail(maximum, Image.Resampling.LANCZOS)
        return image.convert('RGBA').copy()


def load_photo(path, root, maximum=(1800, 1400)):
    item = snapshot(path, root)
    image = preview(path, maximum)
    after = Path(path).stat()
    if (after.st_size, after.st_mtime_ns) != (item.size, item.mtime_ns):
        raise PhotoError('Das Foto wurde während des Ladens verändert. Bitte erneut laden.')
    return item, image
