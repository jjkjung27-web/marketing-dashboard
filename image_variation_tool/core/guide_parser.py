import base64
import io
from PIL import Image

SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}


def image_to_base64(image_bytes: bytes) -> str:
    """Convert image bytes to base64-encoded string."""
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def pdf_to_images(pdf_bytes: bytes) -> list[Image.Image]:
    """Convert PDF to list of PIL Image objects. Requires poppler installation."""
    from pdf2image import convert_from_bytes
    return convert_from_bytes(pdf_bytes, dpi=150)


def prepare_guide_images(file_bytes: bytes, mime_type: str) -> list[tuple[str, str]]:
    """
    Convert guide file to list of (base64, media_type) tuples for Claude Vision.
    
    PDF files are converted page-by-page to PNG (max 3 pages).
    Image files are returned as-is (normalized to image/jpeg for jpg variants).
    
    Args:
        file_bytes: Raw file bytes
        mime_type: MIME type (e.g., "application/pdf", "image/png")
        
    Returns:
        List of (base64_string, media_type) tuples
        
    Raises:
        ValueError: If mime_type is not supported
    """
    if mime_type == "application/pdf":
        images = pdf_to_images(file_bytes)
        result = []
        for img in images[:3]:  # Max 3 pages
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            result.append((image_to_base64(buf.getvalue()), "image/png"))
        return result
    elif mime_type in SUPPORTED_IMAGE_TYPES:
        # Normalize jpg variants to image/jpeg
        normalized = "image/jpeg" if mime_type in {"image/jpg", "image/jpeg"} else mime_type
        return [(image_to_base64(file_bytes), normalized)]
    else:
        raise ValueError(f"Unsupported guide file type: {mime_type}")
