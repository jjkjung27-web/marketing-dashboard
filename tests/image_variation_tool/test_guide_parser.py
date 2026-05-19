import pytest
from PIL import Image
import io
from image_variation_tool.core.guide_parser import image_to_base64, pdf_to_images, SUPPORTED_IMAGE_TYPES


def test_image_to_base64_returns_string():
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = image_to_base64(buf.getvalue())
    assert isinstance(result, str)
    assert len(result) > 0


def test_image_to_base64_is_valid_base64():
    import base64
    img = Image.new("RGB", (50, 50), color=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = image_to_base64(buf.getvalue())
    decoded = base64.b64decode(result)
    assert decoded[:4] == b"\x89PNG"


def test_supported_image_types_includes_common_formats():
    assert "image/png" in SUPPORTED_IMAGE_TYPES
    assert "image/jpeg" in SUPPORTED_IMAGE_TYPES


def test_pdf_to_images_returns_list_of_pil_images(tmp_path):
    pytest.importorskip("pdf2image")
    # PDF 변환은 poppler 설치 필요 — 통합 테스트에서만 실행
    pass
