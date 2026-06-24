from PIL import Image
import base64
import io
import os


def pil_to_base64(image: Image.Image, format: str = 'PNG') -> str:
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    return base64.b64encode(buffer.getvalue()).decode()


def base64_to_pil(base64_str: str) -> Image.Image:
    if base64_str.startswith('data:image'):
        base64_str = base64_str.split(',')[1]
    return Image.open(io.BytesIO(base64.b64decode(base64_str)))


def save_image(image: Image.Image, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image.save(path, quality=95, optimize=True)


def resize_image(image: Image.Image, max_size: int = 1024) -> Image.Image:
    width, height = image.size
    if max(width, height) <= max_size:
        return image
    ratio = max_size / max(width, height)
    new_size = (int(width * ratio), int(height * ratio))
    return image.resize(new_size, Image.Resampling.LANCZOS)