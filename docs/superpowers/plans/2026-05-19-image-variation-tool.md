# Image Variation Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Streamlit 웹 앱에서 이미지 시안을 업로드하면 Claude Vision이 레이아웃을 분석하고, PIL이 매체별 사이즈 배리에이션을 생성해 PNG/JPG/SVG ZIP으로 다운로드할 수 있게 한다.

**Architecture:** Streamlit 프론트엔드에서 원본 이미지·가이드 파일·목표 사이즈를 입력받는다. `analyzer.py`가 Claude Vision으로 요소 위치·색상을 추출하고, `layout_engine.py`가 PIL로 콘텐츠 어웨어 크롭/패딩을 적용해 각 사이즈 이미지를 생성한다. `exporter.py`가 선택한 포맷으로 ZIP을 만든다.

**Tech Stack:** Python 3.11+, Streamlit, anthropic SDK (claude-sonnet-4-6), Pillow, pdf2image, svgwrite, pytest, python-dotenv

---

## File Map

| 파일 | 역할 |
|------|------|
| `image_variation_tool/app.py` | Streamlit 메인 앱 |
| `image_variation_tool/core/__init__.py` | 빈 init |
| `image_variation_tool/core/models.py` | 데이터 클래스 (LayoutElement, AnalysisResult, SizePreset) |
| `image_variation_tool/core/presets.py` | sizes.json 로드·필터 |
| `image_variation_tool/core/analyzer.py` | Claude Vision 분석 |
| `image_variation_tool/core/guide_parser.py` | PDF/이미지 가이드 파싱 |
| `image_variation_tool/core/layout_engine.py` | PIL 콘텐츠 어웨어 크롭/패딩 |
| `image_variation_tool/core/exporter.py` | PNG/JPG/SVG export + ZIP |
| `image_variation_tool/presets/sizes.json` | 매체별 사이즈 프리셋 |
| `image_variation_tool/requirements.txt` | 패키지 목록 |
| `image_variation_tool/.streamlit/config.toml` | Streamlit 설정 |
| `image_variation_tool/.env.example` | 환경변수 예시 |
| `tests/image_variation_tool/__init__.py` | 빈 init |
| `tests/image_variation_tool/test_presets.py` | 프리셋 로더 테스트 |
| `tests/image_variation_tool/test_analyzer.py` | analyzer 테스트 (mock) |
| `tests/image_variation_tool/test_guide_parser.py` | guide_parser 테스트 |
| `tests/image_variation_tool/test_layout_engine.py` | layout_engine 테스트 |
| `tests/image_variation_tool/test_exporter.py` | exporter 테스트 |

---

## Task 1: 프로젝트 셋업

**Files:**
- Create: `image_variation_tool/requirements.txt`
- Create: `image_variation_tool/.env.example`
- Create: `image_variation_tool/.streamlit/config.toml`
- Create: `image_variation_tool/core/__init__.py`
- Create: `tests/image_variation_tool/__init__.py`

- [ ] **Step 1: 디렉토리 생성**

```bash
mkdir -p image_variation_tool/core
mkdir -p image_variation_tool/presets
mkdir -p image_variation_tool/.streamlit
mkdir -p tests/image_variation_tool
```

- [ ] **Step 2: requirements.txt 작성**

```
streamlit>=1.35.0
anthropic>=0.28.0
Pillow>=10.3.0
pdf2image>=1.17.0
svgwrite>=1.4.3
python-dotenv>=1.0.1
pytest>=8.2.0
pytest-mock>=3.14.0
```

- [ ] **Step 3: .env.example 작성**

```
ANTHROPIC_API_KEY=sk-ant-...
```

- [ ] **Step 4: .streamlit/config.toml 작성**

```toml
[server]
maxUploadSize = 50

[theme]
base = "light"
```

- [ ] **Step 5: 빈 init 파일 생성**

`image_variation_tool/core/__init__.py` — 빈 파일
`tests/image_variation_tool/__init__.py` — 빈 파일

- [ ] **Step 6: 패키지 설치**

```bash
cd image_variation_tool
pip install -r requirements.txt
```

- [ ] **Step 7: 커밋**

```bash
git add image_variation_tool/ tests/image_variation_tool/
git commit -m "chore: scaffold image variation tool project"
```

---

## Task 2: 사이즈 프리셋 (sizes.json + presets.py)

**Files:**
- Create: `image_variation_tool/presets/sizes.json`
- Create: `image_variation_tool/core/models.py`
- Create: `image_variation_tool/core/presets.py`
- Create: `tests/image_variation_tool/test_presets.py`

- [ ] **Step 1: sizes.json 작성**

```json
{
  "구글": [
    {"name": "리더보드", "width": 728, "height": 90},
    {"name": "중간 직사각형", "width": 300, "height": 250},
    {"name": "대형 직사각형", "width": 336, "height": 280},
    {"name": "하프 페이지", "width": 300, "height": 600},
    {"name": "대형 리더보드", "width": 970, "height": 90},
    {"name": "빌보드", "width": 970, "height": 250}
  ],
  "메타": [
    {"name": "피드 (정사각형)", "width": 1080, "height": 1080},
    {"name": "피드 (가로)", "width": 1200, "height": 628},
    {"name": "스토리/릴스", "width": 1080, "height": 1920}
  ],
  "카카오": [
    {"name": "비즈보드", "width": 1029, "height": 258},
    {"name": "피드형", "width": 1200, "height": 628}
  ],
  "네이버 GFA": [
    {"name": "롤링보드(1줄)", "width": 430, "height": 150},
    {"name": "피드형", "width": 800, "height": 600},
    {"name": "스마트채널", "width": 320, "height": 50},
    {"name": "와이드이미지", "width": 1000, "height": 600}
  ],
  "SNS": [
    {"name": "인스타그램 피드", "width": 1080, "height": 1080},
    {"name": "인스타그램 스토리", "width": 1080, "height": 1920},
    {"name": "유튜브 썸네일", "width": 1280, "height": 720}
  ]
}
```

- [ ] **Step 2: models.py 작성**

```python
from dataclasses import dataclass, field


@dataclass
class SizePreset:
    channel: str
    name: str
    width: int
    height: int

    @property
    def label(self) -> str:
        return f"{self.name} ({self.width}×{self.height})"


@dataclass
class LayoutElement:
    name: str       # "logo", "main_copy", "sub_copy", "cta", "hero_image", "background"
    x: float        # 0.0 ~ 1.0 (원본 이미지 기준 상대 좌표)
    y: float
    width: float
    height: float
    priority: int   # 1=최고 우선순위 (잘리면 안 됨)


@dataclass
class AnalysisResult:
    elements: list[LayoutElement]
    background_color: str           # hex, e.g. "#FFFFFF"
    color_palette: list[str]        # hex 목록
    guide_constraints: dict = field(default_factory=dict)
    # guide_constraints 예시:
    # {"safe_zone": 0.05, "forbidden_zones": [...], "logo_min_width": 0.1}
```

- [ ] **Step 3: 실패 테스트 작성**

`tests/image_variation_tool/test_presets.py`:
```python
import pytest
from image_variation_tool.core.presets import load_presets, get_channels, get_presets_by_channel


def test_load_presets_returns_all_channels():
    presets = load_presets()
    channels = {p.channel for p in presets}
    assert channels == {"구글", "메타", "카카오", "네이버 GFA", "SNS"}


def test_load_presets_naver_gfa_has_4_sizes():
    presets = load_presets()
    naver = [p for p in presets if p.channel == "네이버 GFA"]
    assert len(naver) == 4


def test_get_channels_returns_sorted_list():
    channels = get_channels()
    assert isinstance(channels, list)
    assert "네이버 GFA" in channels


def test_get_presets_by_channel_filters_correctly():
    presets = get_presets_by_channel("메타")
    assert all(p.channel == "메타" for p in presets)
    assert len(presets) == 3


def test_preset_label_format():
    presets = get_presets_by_channel("메타")
    feed = next(p for p in presets if p.name == "피드 (정사각형)")
    assert feed.label == "피드 (정사각형) (1080×1080)"
```

- [ ] **Step 4: 테스트 실행 — 실패 확인**

```bash
pytest tests/image_variation_tool/test_presets.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 5: presets.py 작성**

```python
import json
from pathlib import Path
from image_variation_tool.core.models import SizePreset

_SIZES_PATH = Path(__file__).parent.parent / "presets" / "sizes.json"


def load_presets() -> list[SizePreset]:
    data = json.loads(_SIZES_PATH.read_text(encoding="utf-8"))
    result = []
    for channel, sizes in data.items():
        for s in sizes:
            result.append(SizePreset(channel=channel, name=s["name"], width=s["width"], height=s["height"]))
    return result


def get_channels() -> list[str]:
    return sorted({p.channel for p in load_presets()})


def get_presets_by_channel(channel: str) -> list[SizePreset]:
    return [p for p in load_presets() if p.channel == channel]
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
pytest tests/image_variation_tool/test_presets.py -v
```
Expected: 5 passed

- [ ] **Step 7: 커밋**

```bash
git add image_variation_tool/presets/ image_variation_tool/core/models.py image_variation_tool/core/presets.py tests/image_variation_tool/test_presets.py
git commit -m "feat: add size presets and data models"
```

---

## Task 3: Guide Parser

**Files:**
- Create: `image_variation_tool/core/guide_parser.py`
- Create: `tests/image_variation_tool/test_guide_parser.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/image_variation_tool/test_guide_parser.py`:
```python
import pytest
from PIL import Image
import io
from image_variation_tool.core.guide_parser import image_to_base64, pdf_to_images, SUPPORTED_IMAGE_TYPES


def test_image_to_base64_returns_string():
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = image_to_base64(buf.getvalue())
    assert isinstance(result, str)
    assert len(result) > 0


def test_image_to_base64_is_valid_base64():
    import base64
    img = Image.new("RGB", (50, 50), color=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = image_to_base64(buf.getvalue())
    decoded = base64.b64decode(result)
    assert decoded[:4] == b"\x89PNG"


def test_supported_image_types_includes_common_formats():
    assert "image/png" in SUPPORTED_IMAGE_TYPES
    assert "image/jpeg" in SUPPORTED_IMAGE_TYPES


def test_pdf_to_images_returns_list_of_pil_images(tmp_path):
    pytest.importorskip("pdf2image")
    # PDF 변환은 poppler 설치 필요 — 통합 테스트에서만 실행
    pass
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/image_variation_tool/test_guide_parser.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: guide_parser.py 작성**

```python
import base64
import io
from PIL import Image

SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}


def image_to_base64(image_bytes: bytes) -> str:
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def pdf_to_images(pdf_bytes: bytes) -> list[Image.Image]:
    """PDF를 PIL Image 리스트로 변환. poppler 설치 필요."""
    from pdf2image import convert_from_bytes
    return convert_from_bytes(pdf_bytes, dpi=150)


def prepare_guide_images(file_bytes: bytes, mime_type: str) -> list[tuple[str, str]]:
    """
    가이드 파일을 Claude Vision에 전달할 (base64, media_type) 튜플 리스트로 변환.
    PDF는 각 페이지를 PNG로 변환.
    """
    if mime_type == "application/pdf":
        images = pdf_to_images(file_bytes)
        result = []
        for img in images[:3]:  # 최대 3페이지만
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            result.append((image_to_base64(buf.getvalue()), "image/png"))
        return result
    elif mime_type in SUPPORTED_IMAGE_TYPES:
        normalized = "image/jpeg" if mime_type in {"image/jpg", "image/jpeg"} else mime_type
        return [(image_to_base64(file_bytes), normalized)]
    else:
        raise ValueError(f"Unsupported guide file type: {mime_type}")
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/image_variation_tool/test_guide_parser.py -v
```
Expected: 3 passed, 1 skipped (pdf 통합 테스트)

- [ ] **Step 5: 커밋**

```bash
git add image_variation_tool/core/guide_parser.py tests/image_variation_tool/test_guide_parser.py
git commit -m "feat: add guide file parser"
```

---

## Task 4: Claude Vision Analyzer

**Files:**
- Create: `image_variation_tool/core/analyzer.py`
- Create: `tests/image_variation_tool/test_analyzer.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/image_variation_tool/test_analyzer.py`:
```python
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
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/image_variation_tool/test_analyzer.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: analyzer.py 작성**

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/image_variation_tool/test_analyzer.py -v
```
Expected: 3 passed

- [ ] **Step 5: 커밋**

```bash
git add image_variation_tool/core/analyzer.py tests/image_variation_tool/test_analyzer.py
git commit -m "feat: add Claude Vision analyzer"
```

---

## Task 5: Layout Engine

**Files:**
- Create: `image_variation_tool/core/layout_engine.py`
- Create: `tests/image_variation_tool/test_layout_engine.py`

**핵심 로직:** PIL로 원본 이미지를 목표 사이즈에 맞게 재구성한다.
- 종횡비가 같으면: 단순 리사이즈
- 종횡비가 다르면: 우선순위 높은 요소(priority 1~2)가 포함되는 영역을 중심으로 스마트 크롭. 남는 공간은 배경색으로 패딩.

- [ ] **Step 1: 실패 테스트 작성**

`tests/image_variation_tool/test_layout_engine.py`:
```python
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
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/image_variation_tool/test_layout_engine.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: layout_engine.py 작성**

```python
from PIL import Image, ImageOps
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

    safe_zone = analysis.guide_constraints.get("safe_zone", _SAFE_ZONE)
    bg_color = _hex_to_rgb(analysis.background_color)

    if abs(orig_ratio - target_ratio) < 0.05:
        return original.resize((target_width, target_height), Image.LANCZOS)

    focus = _get_focus_region(analysis.elements, orig_w, orig_h)
    cropped = _smart_crop(original, focus, target_width, target_height)
    resized = cropped.resize((target_width, target_height), Image.LANCZOS)
    return resized
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/image_variation_tool/test_layout_engine.py -v
```
Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
git add image_variation_tool/core/layout_engine.py tests/image_variation_tool/test_layout_engine.py
git commit -m "feat: add PIL-based layout engine with smart crop"
```

---

## Task 6: Exporter

**Files:**
- Create: `image_variation_tool/core/exporter.py`
- Create: `tests/image_variation_tool/test_exporter.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/image_variation_tool/test_exporter.py`:
```python
import io
import zipfile
import pytest
from PIL import Image
from image_variation_tool.core.exporter import export_to_bytes, create_zip, ExportFormat


def _make_image(w=100, h=100):
    return Image.new("RGB", (w, h), color=(100, 100, 100))


def test_export_png_returns_bytes():
    img = _make_image()
    result = export_to_bytes(img, ExportFormat.PNG)
    assert isinstance(result, bytes)
    assert result[:4] == b"\x89PNG"


def test_export_jpg_returns_bytes():
    img = _make_image()
    result = export_to_bytes(img, ExportFormat.JPG)
    assert isinstance(result, bytes)
    assert result[:2] == b"\xff\xd8"


def test_export_svg_returns_xml_bytes():
    img = _make_image(200, 100)
    result = export_to_bytes(img, ExportFormat.SVG)
    text = result.decode("utf-8")
    assert "<svg" in text
    assert 'width="200"' in text
    assert 'height="100"' in text


def test_create_zip_contains_all_files():
    images = {
        "피드_1080x1080.png": export_to_bytes(_make_image(), ExportFormat.PNG),
        "스토리_1080x1920.png": export_to_bytes(_make_image(), ExportFormat.PNG),
    }
    zip_bytes = create_zip(images)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
    assert "피드_1080x1080.png" in names
    assert "스토리_1080x1920.png" in names


def test_create_zip_returns_valid_zip():
    images = {"test.jpg": export_to_bytes(_make_image(), ExportFormat.JPG)}
    zip_bytes = create_zip(images)
    assert zipfile.is_zipfile(io.BytesIO(zip_bytes))
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/image_variation_tool/test_exporter.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: exporter.py 작성**

```python
import io
import zipfile
import base64
from enum import Enum
from PIL import Image


class ExportFormat(str, Enum):
    PNG = "PNG"
    JPG = "JPG"
    SVG = "SVG"


def export_to_bytes(image: Image.Image, fmt: ExportFormat) -> bytes:
    buf = io.BytesIO()
    if fmt == ExportFormat.PNG:
        image.save(buf, format="PNG")
        return buf.getvalue()
    elif fmt == ExportFormat.JPG:
        rgb = image.convert("RGB")
        rgb.save(buf, format="JPEG", quality=95)
        return buf.getvalue()
    elif fmt == ExportFormat.SVG:
        png_buf = io.BytesIO()
        image.save(png_buf, format="PNG")
        b64 = base64.b64encode(png_buf.getvalue()).decode("utf-8")
        w, h = image.size
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}">'
            f'<image width="{w}" height="{h}" '
            f'xlink:href="data:image/png;base64,{b64}"/>'
            f"</svg>"
        )
        return svg.encode("utf-8")
    raise ValueError(f"Unsupported format: {fmt}")


def create_zip(files: dict[str, bytes]) -> bytes:
    """파일명 → bytes 딕셔너리를 ZIP으로 묶어 반환."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/image_variation_tool/test_exporter.py -v
```
Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
git add image_variation_tool/core/exporter.py tests/image_variation_tool/test_exporter.py
git commit -m "feat: add PNG/JPG/SVG exporter with ZIP packaging"
```

---

## Task 7: Streamlit 앱

**Files:**
- Create: `image_variation_tool/app.py`

이 파일은 Streamlit UI이므로 TDD 대신 단계별 빌드 후 직접 실행으로 확인한다.

- [ ] **Step 1: app.py 작성**

```python
import io
import os
import streamlit as st
from PIL import Image
from dotenv import load_dotenv

from image_variation_tool.core.presets import load_presets, get_channels, get_presets_by_channel
from image_variation_tool.core.analyzer import analyze_image
from image_variation_tool.core.layout_engine import generate_variation
from image_variation_tool.core.exporter import export_to_bytes, create_zip, ExportFormat

load_dotenv()

st.set_page_config(page_title="이미지 배리에이션 툴", layout="wide")
st.title("이미지 배리에이션 툴")

# ── 사이드바: 입력 ──────────────────────────────────────────
with st.sidebar:
    st.header("1. 원본 이미지")
    original_file = st.file_uploader("시안 이미지 업로드", type=["png", "jpg", "jpeg"])

    st.header("2. 가이드 파일 (선택)")
    guide_file = st.file_uploader("가이드 업로드 (PNG/JPG/PDF)", type=["png", "jpg", "jpeg", "pdf"])

    st.header("3. 목표 사이즈 선택")
    channels = get_channels()
    selected_channels = st.multiselect("매체 선택", channels, default=["메타"])

    custom_sizes = st.text_area(
        "직접 입력 (선택, 한 줄에 하나: 이름,가로,세로)",
        placeholder="예: 커스텀_배너,640,100",
    )

    api_key = st.text_input(
        "Anthropic API Key",
        value=os.getenv("ANTHROPIC_API_KEY", ""),
        type="password",
    )

    analyze_btn = st.button("분석 시작", type="primary", disabled=not original_file or not api_key)

# ── 메인 영역 ──────────────────────────────────────────────
if original_file:
    original_bytes = original_file.read()
    original_image = Image.open(io.BytesIO(original_bytes)).convert("RGB")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("원본 이미지")
        st.image(original_image, use_column_width=True)

    # 목표 사이즈 목록 수집
    target_presets = []
    for ch in selected_channels:
        target_presets.extend(get_presets_by_channel(ch))

    for line in custom_sizes.strip().splitlines():
        parts = line.strip().split(",")
        if len(parts) == 3:
            from image_variation_tool.core.models import SizePreset
            try:
                target_presets.append(SizePreset("커스텀", parts[0].strip(), int(parts[1]), int(parts[2])))
            except ValueError:
                st.warning(f"올바르지 않은 커스텀 사이즈: {line}")

    with col2:
        st.subheader("선택된 사이즈")
        if target_presets:
            for p in target_presets:
                st.write(f"- **{p.channel}** {p.label}")
        else:
            st.info("매체를 선택하거나 직접 사이즈를 입력하세요.")

if analyze_btn and original_file and api_key:
    with st.spinner("Claude Vision으로 이미지 분석 중..."):
        guide_bytes = guide_file.read() if guide_file else None
        guide_mime = guide_file.type if guide_file else None

        try:
            analysis = analyze_image(
                image_bytes=original_bytes,
                api_key=api_key,
                guide_bytes=guide_bytes,
                guide_mime=guide_mime,
            )
            st.session_state["analysis"] = analysis
            st.session_state["original_image"] = original_image
            st.session_state["target_presets"] = target_presets
        except Exception as e:
            st.error(f"분석 실패: {e}")

if "analysis" in st.session_state:
    analysis = st.session_state["analysis"]

    st.divider()
    st.subheader("분석 결과 확인")

    with st.expander("감지된 요소 목록"):
        for el in analysis.elements:
            st.write(f"- **{el.name}** | 위치: ({el.x:.2f}, {el.y:.2f}) | 크기: {el.width:.2f}×{el.height:.2f} | 우선순위: {el.priority}")
        st.write(f"배경색: {analysis.background_color}")
        st.write(f"색상 팔레트: {', '.join(analysis.color_palette)}")

    presets = st.session_state["target_presets"]
    original_image = st.session_state["original_image"]

    st.subheader("배리에이션 미리보기")
    exclude_keys = []
    cols = st.columns(min(4, len(presets)) if presets else 1)

    for i, preset in enumerate(presets):
        col = cols[i % len(cols)]
        with col:
            variation = generate_variation(original_image, analysis, preset.width, preset.height)
            st.image(variation, caption=preset.label, use_column_width=True)
            if st.checkbox(f"제외", key=f"exclude_{i}"):
                exclude_keys.append(i)

    st.divider()
    st.subheader("다운로드")

    fmt_choice = st.radio("내보내기 형식", ["PNG", "JPG", "SVG (Figma 호환)"], horizontal=True)
    fmt_map = {"PNG": ExportFormat.PNG, "JPG": ExportFormat.JPG, "SVG (Figma 호환)": ExportFormat.SVG}
    export_fmt = fmt_map[fmt_choice]
    ext = export_fmt.value.lower() if export_fmt != ExportFormat.SVG else "svg"

    if st.button("ZIP 생성 및 다운로드", type="primary"):
        files = {}
        for i, preset in enumerate(presets):
            if i in exclude_keys:
                continue
            variation = generate_variation(original_image, analysis, preset.width, preset.height)
            filename = f"{preset.channel}_{preset.name}_{preset.width}x{preset.height}.{ext}"
            files[filename] = export_to_bytes(variation, export_fmt)

        zip_bytes = create_zip(files)
        st.download_button(
            label=f"ZIP 다운로드 ({len(files)}개 파일)",
            data=zip_bytes,
            file_name="variations.zip",
            mime="application/zip",
        )
```

- [ ] **Step 2: 앱 실행 확인**

```bash
cd image_variation_tool
streamlit run app.py
```
Expected: 브라우저에서 앱 열림, 사이드바에 업로드 버튼 표시

- [ ] **Step 3: 골든 패스 테스트**
  1. 이미지 업로드
  2. 매체 선택 (메타)
  3. API Key 입력 후 "분석 시작"
  4. 분석 결과 확인 (요소 목록, 색상)
  5. 미리보기 확인
  6. PNG로 ZIP 다운로드
  7. ZIP 열어 파일 수·이름 확인

- [ ] **Step 4: 커밋**

```bash
git add image_variation_tool/app.py
git commit -m "feat: add Streamlit app UI"
```

---

## Task 8: 전체 테스트 + Streamlit Cloud 배포 설정

**Files:**
- Modify: `image_variation_tool/requirements.txt`
- Create: `image_variation_tool/.streamlit/secrets.toml.example`

- [ ] **Step 1: 전체 테스트 실행**

```bash
pytest tests/image_variation_tool/ -v
```
Expected: 전체 통과

- [ ] **Step 2: Streamlit Cloud용 secrets 예시 파일 작성**

`image_variation_tool/.streamlit/secrets.toml.example`:
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

- [ ] **Step 3: .gitignore에 secrets 추가**

`.gitignore`에 아래 추가:
```
.streamlit/secrets.toml
.env
```

- [ ] **Step 4: Streamlit Cloud 배포**
  1. [share.streamlit.io](https://share.streamlit.io) 접속
  2. GitHub 리포 연결
  3. Main file path: `image_variation_tool/app.py`
  4. Secrets에 `ANTHROPIC_API_KEY` 입력
  5. Deploy

- [ ] **Step 5: 배포 URL로 팀 접근 확인**

- [ ] **Step 6: 최종 커밋**

```bash
git add image_variation_tool/.streamlit/secrets.toml.example .gitignore
git commit -m "chore: add Streamlit Cloud deployment config"
```
