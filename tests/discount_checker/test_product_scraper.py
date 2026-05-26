from unittest.mock import patch, MagicMock
from tools.discount_checker.cache import Cache, CACHE_MISS
from tools.discount_checker.product_scraper import ProductScraper, _parse_discount_from_html


def test_get_max_discount_returns_cached(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    cache.set("uid:1234567", 65, ttl_seconds=86400)
    scraper = ProductScraper(cache)
    result = scraper.get_max_discount(["1234567"])
    assert result["1234567"] == 65


def test_get_max_discount_multiple_uids_cached(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    cache.set("uid:111", 50, ttl_seconds=86400)
    cache.set("uid:222", 70, ttl_seconds=86400)
    scraper = ProductScraper(cache)
    result = scraper.get_max_discount(["111", "222"])
    assert result == {"111": 50, "222": 70}


def test_parse_discount_from_html_json_field():
    html = '<script>{"discountRate": 68}</script>'
    assert _parse_discount_from_html(html) == 68


def test_parse_discount_from_html_percent_text():
    html = "<span>70% 할인</span>"
    assert _parse_discount_from_html(html) == 70


def test_parse_discount_from_html_off_text():
    html = "<div>50% OFF</div>"
    assert _parse_discount_from_html(html) == 50


def test_parse_discount_from_html_multiple_returns_max():
    html = '<script>{"discountRate": 30}</script><span>70% 할인</span>'
    assert _parse_discount_from_html(html) == 70


def test_parse_discount_from_html_none_when_not_found():
    html = "<html><body>할인 없음</body></html>"
    assert _parse_discount_from_html(html) is None


def test_get_max_discount_scrape_failure_returns_none(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    scraper = ProductScraper(cache)
    with patch("tools.discount_checker.product_scraper._scrape_discount", side_effect=Exception("timeout")):
        result = scraper.get_max_discount(["9999999"])
    assert result["9999999"] is None
