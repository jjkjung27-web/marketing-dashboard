import json
import re
import io
import base64
import requests
from PIL import Image
from image_variation_tool.core.models import AnalysisResult, LayoutElement
from image_variation_tool.core.guide_parser import prepare_guide_images

_SYSTEM_PROMPT = """당신은 광고 디자인 레이아웃 분석 전문가입니다.
이미지를 분석하고 반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.

{
  "elements": [
    {
      "name": "요소명 (logo/main_copy/sub_copy/cta/hero_image/background 중 하나)",
      "x": 0.0,
      "y": 0.0,
      "width": 1.0,
      "height": 1.0,
      "priority": 1
    }
  ],
  "background_color": "#FFFFFF",
  "color_palette": ["#FFFFFF"],
  "guide_constraints": {
    "safe_zone": 0.05
  }
}"""

_USER_PROMPT = "이 이미지의 레이아웃 요소를 분석해주세요. 반드시 JSON만 응답하세요."
_USER_PROMPT_WITH_GUIDE = "첫 번째 이미지는 원본 시안이고, 나머지는 디자인 가이드입니다. 가이드를 참고해 원본 시안의 레이아웃 요소를 분석해주세요. 반드시 JSON만 응답하세요."


def _parse_response(text: str) -> AnalysisResult:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match is None:
        raise ValueError(f"No JSON found in response: {text[:200]}")
    raw = match.group(0)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in response: {e}\nRaw: {raw[:200]}") from e
    elements = [
        LayoutElement(
            name=e["name"],
            x=float(e["x"]),
            y=float(e["y"]),
            width=float(e["width"]),
            height=float(e["height"]),
            priority=int(e["priority"]),
        )
        for e in data.get("elements", [])
    ]
    return AnalysisResult(
        elements=elements,
        background_color=data.get("background_color", "#FFFFFF"),
        color_palette=data.get("color_palette", []),
        guide_constraints=data.get("guide_constraints", {}),
    )


_GEMINI_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"


def _image_to_inline(image: Image.Image) -> dict:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(buf.getvalue()).decode()}}


def analyze_image(
    image_bytes: bytes,
    api_key: str,
    image_mime: str = "image/png",
    guide_bytes: bytes | None = None,
    guide_mime: str | None = None,
) -> AnalysisResult:
    original_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    parts: list = [_image_to_inline(original_image)]

    if guide_bytes and guide_mime:
        guide_list = prepare_guide_images(guide_bytes, guide_mime)
        for b64, _ in guide_list:
            guide_img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
            parts.append(_image_to_inline(guide_img))

    prompt = _USER_PROMPT_WITH_GUIDE if (guide_bytes and guide_mime) else _USER_PROMPT
    parts.append({"text": prompt})

    payload = {
        "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
        "contents": [{"parts": parts}],
    }

    resp = requests.post(_GEMINI_URL, params={"key": api_key}, json=payload, timeout=60)
    if not resp.ok:
        raise ValueError(f"{resp.status_code} {resp.text}")

    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return _parse_response(text)
