import tempfile
import unittest
from pathlib import Path
from PIL import Image
from fotoswipe.imaging import load_photo, preview


class ImagingTests(unittest.TestCase):
    def test_exif_orientation_and_bounded_preview(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'rotated.jpg'
            image = Image.new('RGB', (160, 90), 'green')
            exif = image.getexif(); exif[274] = 6
            image.save(path, exif=exif)
            item, rendered = load_photo(path, folder)
            self.assertEqual(rendered.size, (90, 160))
            self.assertEqual(len(item.sha256), 64)
            self.assertTrue(path.exists())
            tiny = preview(path, (40, 40))
            self.assertLessEqual(max(tiny.size), 40)

    @unittest.skipUnless('.heic' in Image.registered_extensions(), 'HEIC plugin not installed in local analysis runtime')
    def test_heic_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'iphone.heic'
            Image.new('RGB', (64, 48), 'blue').save(path, format='HEIF')
            _, rendered = load_photo(path, folder)
            self.assertEqual(rendered.size, (64, 48))


if __name__ == '__main__': unittest.main()
