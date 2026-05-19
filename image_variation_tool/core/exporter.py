import io
import zipfile
import base64
from enum import Enum
from PIL import Image


class ExportFormat(str, Enum):
    PNG = "PNG"
    JPG = "JPG"
    SVG = "SVG"


def export_to_bytes(image: Image.Image, fmt: ExportFormat) -> bytes:
    buf = io.BytesIO()
    if fmt == ExportFormat.PNG:
        image.save(buf, format="PNG")
        return buf.getvalue()
    elif fmt == ExportFormat.JPG:
        rgb = image.convert("RGB")
        rgb.save(buf, format="JPEG", quality=95)
        return buf.getvalue()
    elif fmt == ExportFormat.SVG:
        png_buf = io.BytesIO()
        image.save(png_buf, format="PNG")
        b64 = base64.b64encode(png_buf.getvalue()).decode("utf-8")
        w, h = image.size
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}">'
            f'<image width="{w}" height="{h}" '
            f'xlink:href="data:image/png;base64,{b64}"/>'
            f"</svg>"
        )
        return svg.encode("utf-8")
    raise ValueError(f"Unsupported format: {fmt}")


def create_zip(files: dict[str, bytes]) -> bytes:
    """파일명 → bytes 딕셔너리를 ZIP으로 묶어 반환."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()
