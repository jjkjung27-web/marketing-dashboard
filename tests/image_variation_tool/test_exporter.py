import io
import zipfile
import pytest
from PIL import Image
from image_variation_tool.core.exporter import export_to_bytes, create_zip, ExportFormat


def _make_image(w=100, h=100):
    return Image.new("RGB", (w, h), color=(100, 100, 100))


def test_export_png_returns_bytes():
    img = _make_image()
    result = export_to_bytes(img, ExportFormat.PNG)
    assert isinstance(result, bytes)
    assert result[:4] == b"\x89PNG"


def test_export_jpg_returns_bytes():
    img = _make_image()
    result = export_to_bytes(img, ExportFormat.JPG)
    assert isinstance(result, bytes)
    assert result[:2] == b"\xff\xd8"


def test_export_svg_returns_xml_bytes():
    img = _make_image(200, 100)
    result = export_to_bytes(img, ExportFormat.SVG)
    text = result.decode("utf-8")
    assert "<svg" in text
    assert 'width="200"' in text
    assert 'height="100"' in text


def test_create_zip_contains_all_files():
    images = {
        "피드_1080x1080.png": export_to_bytes(_make_image(), ExportFormat.PNG),
        "스토리_1080x1920.png": export_to_bytes(_make_image(), ExportFormat.PNG),
    }
    zip_bytes = create_zip(images)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
    assert "피드_1080x1080.png" in names
    assert "스토리_1080x1920.png" in names


def test_create_zip_returns_valid_zip():
    images = {"test.jpg": export_to_bytes(_make_image(), ExportFormat.JPG)}
    zip_bytes = create_zip(images)
    assert zipfile.is_zipfile(io.BytesIO(zip_bytes))
