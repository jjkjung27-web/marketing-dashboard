from unittest.mock import patch, MagicMock
from tools.discount_checker.cache import Cache, CACHE_MISS
from tools.discount_checker.image_analyzer import ImageAnalyzer, _detect_media_type


def test_returns_cached_value(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    cache.set("image:cid1:abc123", 70)
    analyzer = ImageAnalyzer("fake_key", cache)

    with patch("tools.discount_checker.image_analyzer._download_and_hash") as mock_dl:
        mock_dl.return_value = (b"imgdata", "abc123")
        result = analyzer.extract_discount("cid1", "http://example.com/img.jpg")

    assert result == 70


def test_returns_cached_none(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    cache.set("image:cid2:xyz", None)
    analyzer = ImageAnalyzer("fake_key", cache)

    with patch("tools.discount_checker.image_analyzer._download_and_hash") as mock_dl:
        mock_dl.return_value = (b"data", "xyz")
        result = analyzer.extract_discount("cid2", "http://example.com/img.jpg")

    assert result is None


def test_calls_claude_and_parses_number(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    analyzer = ImageAnalyzer("fake_key", cache)

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="70")]

    with patch("tools.discount_checker.image_analyzer._download_and_hash") as mock_dl, \
         patch.object(analyzer._client.messages, "create", return_value=mock_msg):
        mock_dl.return_value = (b"imgdata", "newhash1")
        result = analyzer.extract_discount("cid3", "http://example.com/img.jpg")

    assert result == 70


def test_calls_claude_and_returns_none_for_null(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    analyzer = ImageAnalyzer("fake_key", cache)

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="null")]

    with patch("tools.discount_checker.image_analyzer._download_and_hash") as mock_dl, \
         patch.object(analyzer._client.messages, "create", return_value=mock_msg):
        mock_dl.return_value = (b"imgdata", "newhash2")
        result = analyzer.extract_discount("cid4", "http://example.com/img.jpg")

    assert result is None


def test_detect_media_type_png():
    assert _detect_media_type("http://example.com/img.png") == "image/png"


def test_detect_media_type_jpeg_default():
    assert _detect_media_type("http://example.com/img.jpg") == "image/jpeg"
    assert _detect_media_type("http://example.com/img") == "image/jpeg"


def test_detect_media_type_webp():
    assert _detect_media_type("http://example.com/img.webp") == "image/webp"
