import re
from playwright.sync_api import sync_playwright

from tools.discount_checker.cache import Cache, CACHE_MISS

MUSINSA_PRODUCT_URL = "https://www.musinsa.com/products/{uid}"
CACHE_TTL = 24 * 3600


def _parse_discount_from_html(html: str) -> int | None:
    candidates = []

    # JSON field: "discountRate": 68
    for m in re.finditer(r'"discountRate":\s*(\d+)', html):
        candidates.append(int(m.group(1)))

    # Text pattern: "70% 할인" or "70% OFF"
    for m in re.finditer(r'(\d+)%\s*(?:할인|OFF|off)', html):
        candidates.append(int(m.group(1)))

    return max(candidates) if candidates else None


def _scrape_discount(uid: str) -> int | None:
    url = MUSINSA_PRODUCT_URL.format(uid=uid)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)

            # CSS selector 시도 (무신사 실제 클래스명 확인 후 조정 필요)
            discount_el = page.query_selector("[class*='discount'][class*='rate'], [class*='sale-rate']")
            if discount_el:
                text = discount_el.inner_text()
                m = re.search(r"(\d+)", text)
                if m:
                    return int(m.group(1))

            # Fallback: 전체 HTML에서 패턴 추출
            content = page.content()
            return _parse_discount_from_html(content)
        finally:
            browser.close()


class ProductScraper:
    def __init__(self, cache: Cache):
        self._cache = cache

    def get_max_discount(self, uids: list[str]) -> dict[str, int | None]:
        results = {}
        for uid in uids:
            cache_key = f"uid:{uid}"
            cached = self._cache.get(cache_key)
            if cached is not CACHE_MISS:
                results[uid] = cached
                continue
            try:
                rate = _scrape_discount(uid)
            except Exception:
                rate = None
            ttl = CACHE_TTL if rate is not None else 3600
            self._cache.set(cache_key, rate, ttl_seconds=ttl)
            results[uid] = rate
        return results
