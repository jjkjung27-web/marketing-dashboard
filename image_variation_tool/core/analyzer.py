import json
import re
import anthropic
from image_variation_tool.core.models import AnalysisResult, LayoutElement
from image_variation_tool.core.guide_parser import image_to_base64, prepare_guide_images

_SYSTEM_PROMPT = """당신은 광고 디자인 레이아웃 분석 전문가입니다.
이미지를 분석하고 반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.

{
  "elements": [
    {
      "name": "요소명 (logo/main_copy/sub_copy/cta/hero_image/background 중 하나)",
      "x": 0.0 ~ 1.0 (왼쪽 기준 상대 좌표),
      "y": 0.0 ~ 1.0 (위쪽 기준 상대 좌표),
      "width": 0.0 ~ 1.0,
      "height": 0.0 ~ 1.0,
      "priority": 1~5 (1=반드시 보존, 5=잘려도 됨)
    }
  ],
  "background_color": "#RRGGBB",
  "color_palette": ["#RRGGBB", ...],
  "guide_constraints": {
    "safe_zone": 0.05,
    "logo_min_width": 0.1
  }
}"""

_USER_PROMPT = "이 이미지의 레이아웃 요소를 분석해주세요."
_USER_PROMPT_WITH_GUIDE = "첫 번째 이미지는 원본 시안이고, 나머지는 디자인 가이드입니다. 가이드를 참고해 원본 시안의 레이아웃 요소를 분석해주세요."


def _parse_claude_response(text: str) -> AnalysisResult:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    raw = match.group(0) if match else text
    data = json.loads(raw)
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


def analyze_image(
    image_bytes: bytes,
    api_key: str,
    guide_bytes: bytes | None = None,
    guide_mime: str | None = None,
) -> AnalysisResult:
    client = anthropic.Anthropic(api_key=api_key)

    image_content: list[dict] = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": image_to_base64(image_bytes),
            },
        }
    ]

    if guide_bytes and guide_mime:
        guide_images = prepare_guide_images(guide_bytes, guide_mime)
        for b64, mime in guide_images:
            image_content.append(
                {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}}
            )

    prompt = _USER_PROMPT_WITH_GUIDE if guide_bytes else _USER_PROMPT
    image_content.append({"type": "text", "text": prompt})

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": image_content}],
    )

    return _parse_claude_response(message.content[0].text)
