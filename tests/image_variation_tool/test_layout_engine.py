import pytest
from PIL import Image
from image_variation_tool.core.models import AnalysisResult, LayoutElement
from image_variation_tool.core.layout_engine import generate_variation, _get_focus_region


def _make_analysis(elements=None):
    if elements is None:
        elements = [
            LayoutElement("logo", 0.05, 0.05, 0.2, 0.1, priority=1),
            LayoutElement("main_copy", 0.1, 0.3, 0.8, 0.2, priority=2),
        ]
    return AnalysisResult(
        elements=elements,
        background_color="#FFFFFF",
        color_palette=["#FFFFFF"],
    )


def test_generate_variation_returns_pil_image():
    original = Image.new("RGB", (1080, 1080), color=(200, 200, 200))
    analysis = _make_analysis()
    result = generate_variation(original, analysis, target_width=1200, target_height=628)
    assert isinstance(result, Image.Image)


def test_generate_variation_output_has_correct_size():
    original = Image.new("RGB", (1080, 1080), color=(200, 200, 200))
    analysis = _make_analysis()
    result = generate_variation(original, analysis, target_width=300, target_height=250)
    assert result.size == (300, 250)


def test_generate_variation_same_aspect_ratio():
    original = Image.new("RGB", (1080, 1080), color=(100, 150, 200))
    analysis = _make_analysis()
    result = generate_variation(original, analysis, target_width=600, target_height=600)
    assert result.size == (600, 600)


def test_get_focus_region_covers_priority_elements():
    orig_w, orig_h = 1080, 1080
    elements = [
        LayoutElement("logo", 0.05, 0.05, 0.2, 0.1, priority=1),
        LayoutElement("main_copy", 0.1, 0.4, 0.8, 0.2, priority=2),
        LayoutElement("background", 0.0, 0.0, 1.0, 1.0, priority=5),
    ]
    region = _get_focus_region(elements, orig_w, orig_h)
    left, top, right, bottom = region
    assert left <= int(0.05 * orig_w)
    assert top <= int(0.05 * orig_h)
    assert right >= int((0.05 + 0.2) * orig_w)
    assert bottom >= int((0.4 + 0.2) * orig_h)


def test_generate_variation_with_no_elements():
    original = Image.new("RGB", (800, 600), color=(255, 255, 255))
    analysis = AnalysisResult(elements=[], background_color="#FFFFFF", color_palette=[])
    result = generate_variation(original, analysis, target_width=300, target_height=250)
    assert result.size == (300, 250)
