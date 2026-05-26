import base64
import hashlib
import re
import urllib.request

import anthropic

from tools.discount_checker.cache import Cache, CACHE_MISS


def _download_and_hash(url: str) -> tuple[bytes, str]:
    data = urllib.request.urlopen(url, timeout=15).read()
    return data, hashlib.sha256(data).hexdigest()


def _detect_media_type(url: str) -> str:
    url_lower = url.lower().split("?")[0]
    if url_lower.endswith(".png"):
        return "image/png"
    if url_lower.endswith(".gif"):
        return "image/gif"
    if url_lower.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"


class ImageAnalyzer:
    def __init__(self, api_key: str, cache: Cache):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._cache = cache

    def extract_discount(self, creative_id: str, image_url: str) -> int | None:
        image_data, image_hash = _download_and_hash(image_url)
        cache_key = f"image:{creative_id}:{image_hash}"

        cached = self._cache.get(cache_key)
        if cached is not CACHE_MISS:
            return cached

        message = self._client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=64,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": _detect_media_type(image_url),
                            "data": base64.standard_b64encode(image_data).decode("utf-8"),
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "이 광고 이미지에서 할인율(%)을 숫자만 추출해줘. "
                            "'최대 70%', '70% OFF' 같은 텍스트에서 숫자만. "
                            "할인율이 없으면 null이라고만 답해. "
                            "숫자 하나 또는 null만 출력."
                        ),
                    },
                ],
            }],
        )

        text = message.content[0].text.strip()

        if text.lower() == "null" or not text:
            result = None
        else:
            m = re.search(r"(\d+)", text)
            result = int(m.group(1)) if m else None

        self._cache.set(cache_key, result)  # 영구 캐시 (이미지 hash 변경 시 자동 무효화)
        return result
