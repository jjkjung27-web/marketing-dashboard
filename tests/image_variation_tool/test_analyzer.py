import pytest
from unittest.mock import MagicMock, patch
from image_variation_tool.core.models import AnalysisResult, LayoutElement
from image_variation_tool.core.analyzer import analyze_image, _parse_claude_response


def test_parse_claude_response_extracts_elements():
    raw = """
    {
      "elements": [
        {"name": "logo", "x": 0.05, "y": 0.05, "width": 0.2, "height": 0.1, "priority": 1},
        {"name": "main_copy", "x": 0.1, "y": 0.3, "width": 0.8, "height": 0.15, "priority": 2}
      ],
      "background_color": "#F5F5F5",
      "color_palette": ["#FF0000", "#FFFFFF", "#333333"],
      "guide_constraints": {}
    }
    """
    result = _parse_claude_response(raw)
    assert isinstance(result, AnalysisResult)
    assert len(result.elements) == 2
    assert result.elements[0].name == "logo"
    assert result.elements[0].priority == 1
    assert result.background_color == "#F5F5F5"
    assert len(result.color_palette) == 3


def test_parse_claude_response_handles_missing_guide_constraints():
    raw = """
    {
      "elements": [],
      "background_color": "#FFFFFF",
      "color_palette": []
    }
    """
    result = _parse_claude_response(raw)
    assert result.guide_constraints == {}


def test_analyze_image_calls_claude_api(tmp_path):
    from PIL import Image
    import io

    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    image_bytes = buf.getvalue()

    mock_response_text = '''
    {
      "elements": [
        {"name": "background", "x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0, "priority": 5}
      ],
      "background_color": "#FFFFFF",
      "color_palette": ["#FFFFFF"],
      "guide_constraints": {}
    }
    '''

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=mock_response_text)]

    with patch("image_variation_tool.core.analyzer.anthropic.Anthropic") as MockClient:
        mock_client = MockClient.return_value
        mock_client.messages.create.return_value = mock_message
        result = analyze_image(image_bytes, api_key="test-key")

    assert isinstance(result, AnalysisResult)
    assert result.background_color == "#FFFFFF"
