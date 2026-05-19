from PIL import Image
from image_variation_tool.core.models import AnalysisResult, LayoutElement

_SAFE_ZONE = 0.05  # 기본 안전 여백 비율


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _get_focus_region(
    elements: list[LayoutElement], orig_w: int, orig_h: int
) -> tuple[int, int, int, int]:
    """priority 1~2 요소를 모두 포함하는 최소 bounding box 반환 (pixel)."""
    priority_els = [e for e in elements if e.priority <= 2]
    if not priority_els:
        return (0, 0, orig_w, orig_h)

    left = min(int(e.x * orig_w) for e in priority_els)
    top = min(int(e.y * orig_h) for e in priority_els)
    right = max(int((e.x + e.width) * orig_w) for e in priority_els)
    bottom = max(int((e.y + e.height) * orig_h) for e in priority_els)

    pad_x = int(orig_w * _SAFE_ZONE)
    pad_y = int(orig_h * _SAFE_ZONE)
    return (
        max(0, left - pad_x),
        max(0, top - pad_y),
        min(orig_w, right + pad_x),
        min(orig_h, bottom + pad_y),
    )


def _smart_crop(image: Image.Image, focus: tuple, target_w: int, target_h: int) -> Image.Image:
    """focus 영역을 중심으로 target 비율에 맞게 크롭."""
    orig_w, orig_h = image.size
    fl, ft, fr, fb = focus
    focus_cx = (fl + fr) // 2
    focus_cy = (ft + fb) // 2

    target_ratio = target_w / target_h
    orig_ratio = orig_w / orig_h

    if orig_ratio > target_ratio:
        crop_h = orig_h
        crop_w = int(orig_h * target_ratio)
    else:
        crop_w = orig_w
        crop_h = int(orig_w / target_ratio)

    left = max(0, min(focus_cx - crop_w // 2, orig_w - crop_w))
    top = max(0, min(focus_cy - crop_h // 2, orig_h - crop_h))
    return image.crop((left, top, left + crop_w, top + crop_h))


def generate_variation(
    original: Image.Image,
    analysis: AnalysisResult,
    target_width: int,
    target_height: int,
) -> Image.Image:
    orig_w, orig_h = original.size
    orig_ratio = orig_w / orig_h
    target_ratio = target_width / target_height

    if abs(orig_ratio - target_ratio) < 0.05:
        return original.resize((target_width, target_height), Image.LANCZOS)

    focus = _get_focus_region(analysis.elements, orig_w, orig_h)
    cropped = _smart_crop(original, focus, target_width, target_height)
    resized = cropped.resize((target_width, target_height), Image.LANCZOS)
    return resized
