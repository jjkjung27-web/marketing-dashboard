# 광고 소재 할인율 검수 자동화 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 메타 광고 소재 이미지의 할인율을 Claude Vision으로 추출하고 무신사 상품 페이지 실제 할인율과 비교하여 불일치를 CSV + Slack으로 보고한다.

**Architecture:** Google Sheets URL을 CLI로 입력받아 광고명·UID 목록을 읽고, Meta API로 소재 이미지를 조회, Claude Vision으로 이미지 내 할인율을 추출, Playwright로 무신사 상품 페이지를 스크래핑, 0% 오차 기준으로 비교한다. JSON 파일 캐시로 재실행 시 중복 API 호출을 방지한다.

**Tech Stack:** Python 3.12+, anthropic, facebook-business, playwright, google-api-python-client, google-auth, python-dotenv, pytest

---

## 파일 구조

```
tools/discount_checker/
  __init__.py
  config.py            # 환경변수 로딩
  cache.py             # JSON 캐시 (TTL + CACHE_MISS 센티널)
  comparator.py        # 할인율 비교 순수 로직 + 데이터 클래스
  reporter.py          # CSV 저장 + Slack 웹훅
  sheet_reader.py      # Sheets URL 파싱 + 데이터 추출
  product_scraper.py   # Playwright로 musinsa 스크래핑
  image_analyzer.py    # Claude Vision으로 할인율 추출
  meta_client.py       # Meta Marketing API
  check.py             # CLI 진입점 (argparse + 파이프라인 조율)

tests/discount_checker/
  __init__.py
  test_cache.py
  test_comparator.py
  test_reporter.py
  test_sheet_reader.py
  test_product_scraper.py
  test_image_analyzer.py

output/               # discount_check_YYYY-MM-DD.csv 저장
cache/                # discount_check_cache.json 저장
```

---

## Task 1: 스캐폴드 + 의존성

**Files:**
- Create: `tools/discount_checker/__init__.py`
- Create: `tests/discount_checker/__init__.py`
- Modify: `requirements.txt` (없으면 신규 생성)

- [ ] **Step 1: 디렉토리 및 빈 파일 생성**

```bash
mkdir -p tools/discount_checker tests/discount_checker output cache
touch tools/discount_checker/__init__.py
touch tests/discount_checker/__init__.py
```

- [ ] **Step 2: 의존성 추가**

`requirements.txt` 에 아래 추가 (없으면 신규 생성):

```
anthropic>=0.30.0
facebook-business>=18.0.0
playwright>=1.40.0
google-api-python-client>=2.100.0
google-auth>=2.20.0
python-dotenv>=1.0.0
pytest>=8.0.0
```

- [ ] **Step 3: 설치**

```bash
pip install -r requirements.txt
playwright install chromium
```

Expected: 설치 완료 메시지 출력, 오류 없음.

- [ ] **Step 4: `.env` 파일 생성** (git ignore 대상, 실제 값 입력 필요)

```bash
cat > .env << 'EOF'
META_ACCESS_TOKEN=your_meta_access_token_here
META_AD_ACCOUNT_ID=act_XXXXXXXXX
ANTHROPIC_API_KEY=your_anthropic_api_key_here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json
EOF
```

> **참고:** Google Sheets 접근을 위해 GCP 서비스 계정 JSON 파일(`service_account.json`)이 필요하다. GCP 콘솔 → IAM → 서비스 계정 → 키 생성(JSON). 생성한 계정에 대상 스프레드시트 편집 권한 부여.

- [ ] **Step 5: 커밋**

```bash
git add tools/discount_checker/__init__.py tests/discount_checker/__init__.py requirements.txt
git commit -m "feat: scaffold discount_checker tool"
```

---

## Task 2: cache.py

**Files:**
- Create: `tools/discount_checker/cache.py`
- Create: `tests/discount_checker/test_cache.py`

- [ ] **Step 1: 테스트 작성**

`tests/discount_checker/test_cache.py`:

```python
import time
from tools.discount_checker.cache import Cache, CACHE_MISS


def test_miss_returns_cache_miss_sentinel(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    assert cache.get("missing") is CACHE_MISS


def test_set_and_get(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    cache.set("key1", 70)
    assert cache.get("key1") == 70


def test_set_none_is_distinguishable_from_miss(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    cache.set("key1", None)
    result = cache.get("key1")
    assert result is not CACHE_MISS
    assert result is None


def test_ttl_expiry(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    cache.set("key2", 50, ttl_seconds=1)
    assert cache.get("key2") == 50
    time.sleep(1.1)
    assert cache.get("key2") is CACHE_MISS


def test_permanent_entry_survives(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    cache.set("key3", 30, ttl_seconds=None)
    time.sleep(0.1)
    assert cache.get("key3") == 30


def test_persists_across_instances(tmp_path):
    path = tmp_path / "cache.json"
    Cache(path).set("key4", 99)
    assert Cache(path).get("key4") == 99
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/discount_checker/test_cache.py -v
```

Expected: `ImportError` 또는 `ModuleNotFoundError`

- [ ] **Step 3: 구현 작성**

`tools/discount_checker/cache.py`:

```python
import json
import time
from pathlib import Path
from typing import Any

CACHE_MISS = object()


class Cache:
    def __init__(self, path: Path):
        self._path = path
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            return json.loads(self._path.read_text(encoding="utf-8"))
        return {}

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get(self, key: str) -> Any:
        entry = self._data.get(key)
        if entry is None:
            return CACHE_MISS
        if entry.get("expires_at") and time.time() > entry["expires_at"]:
            del self._data[key]
            self._save()
            return CACHE_MISS
        return entry["value"]

    def set(self, key: str, value: Any, ttl_seconds: int | None = None):
        self._data[key] = {
            "value": value,
            "expires_at": time.time() + ttl_seconds if ttl_seconds else None,
        }
        self._save()
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/discount_checker/test_cache.py -v
```

Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add tools/discount_checker/cache.py tests/discount_checker/test_cache.py
git commit -m "feat: add JSON cache with TTL and CACHE_MISS sentinel"
```

---

## Task 3: comparator.py

**Files:**
- Create: `tools/discount_checker/comparator.py`
- Create: `tests/discount_checker/test_comparator.py`

- [ ] **Step 1: 테스트 작성**

`tests/discount_checker/test_comparator.py`:

```python
from tools.discount_checker.comparator import AdRow, CompareResult, compare


def test_exact_match_returns_일치():
    result = compare("ad_A", 70, {"uid1": 70, "uid2": 60})
    assert result.status == "일치"
    assert result.diff == 0
    assert result.representative_uid == "uid1"
    assert result.actual_max_discount == 70


def test_mismatch_creative_higher_returns_불일치():
    result = compare("ad_B", 70, {"uid1": 68})
    assert result.status == "불일치"
    assert result.diff == 2
    assert result.actual_max_discount == 68


def test_mismatch_creative_lower_returns_불일치():
    result = compare("ad_C", 60, {"uid1": 65})
    assert result.status == "불일치"
    assert result.diff == -5


def test_none_creative_discount_returns_추출불가():
    result = compare("ad_D", None, {"uid1": 70})
    assert result.status == "추출불가"
    assert result.creative_discount is None


def test_all_uids_none_returns_스크래핑실패():
    result = compare("ad_E", 70, {"uid1": None, "uid2": None})
    assert result.status == "스크래핑실패"
    assert result.actual_max_discount is None


def test_max_uid_selected_as_representative():
    result = compare("ad_F", 50, {"uid1": 30, "uid2": 50, "uid3": 40})
    assert result.representative_uid == "uid2"
    assert result.actual_max_discount == 50


def test_mixed_none_and_valid_uids_uses_valid():
    result = compare("ad_G", 70, {"uid1": None, "uid2": 70})
    assert result.status == "일치"
    assert result.representative_uid == "uid2"


def test_adrow_dataclass():
    row = AdRow(ad_name="ad_A", uids=["uid1", "uid2"])
    assert row.ad_name == "ad_A"
    assert row.uids == ["uid1", "uid2"]
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/discount_checker/test_comparator.py -v
```

Expected: `ImportError`

- [ ] **Step 3: 구현 작성**

`tools/discount_checker/comparator.py`:

```python
from dataclasses import dataclass


@dataclass
class AdRow:
    ad_name: str
    uids: list[str]


@dataclass
class CompareResult:
    ad_name: str
    creative_discount: int | None
    representative_uid: str | None
    actual_max_discount: int | None
    diff: int | None
    status: str  # "일치" | "불일치" | "조회실패" | "추출불가" | "스크래핑실패"


def compare(
    ad_name: str,
    creative_discount: int | None,
    uid_discounts: dict[str, int | None],
) -> CompareResult:
    if creative_discount is None:
        return CompareResult(ad_name, None, None, None, None, "추출불가")

    valid = {uid: rate for uid, rate in uid_discounts.items() if rate is not None}
    if not valid:
        return CompareResult(ad_name, creative_discount, None, None, None, "스크래핑실패")

    rep_uid = max(valid, key=lambda u: valid[u])
    actual_max = valid[rep_uid]
    diff = creative_discount - actual_max
    status = "일치" if diff == 0 else "불일치"
    return CompareResult(ad_name, creative_discount, rep_uid, actual_max, diff, status)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/discount_checker/test_comparator.py -v
```

Expected: 8 passed

- [ ] **Step 5: 커밋**

```bash
git add tools/discount_checker/comparator.py tests/discount_checker/test_comparator.py
git commit -m "feat: add comparator with AdRow and CompareResult"
```

---

## Task 4: reporter.py

**Files:**
- Create: `tools/discount_checker/reporter.py`
- Create: `tests/discount_checker/test_reporter.py`

- [ ] **Step 1: 테스트 작성**

`tests/discount_checker/test_reporter.py`:

```python
import csv
from tools.discount_checker.comparator import CompareResult
from tools.discount_checker.reporter import write_csv


def test_write_csv_creates_file(tmp_path):
    results = [CompareResult("ad_A", 70, "uid1", 70, 0, "일치")]
    path = write_csv(results, tmp_path)
    assert path.exists()


def test_write_csv_filename_contains_date(tmp_path):
    results = [CompareResult("ad_A", 70, "uid1", 70, 0, "일치")]
    path = write_csv(results, tmp_path)
    assert "discount_check_" in path.name
    assert path.suffix == ".csv"


def test_write_csv_headers(tmp_path):
    results = [CompareResult("ad_A", 70, "uid1", 70, 0, "일치")]
    path = write_csv(results, tmp_path)
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        assert set(reader.fieldnames) == {
            "검수일시", "광고명", "소재_할인율", "대표_UID", "실제_최대_할인율", "오차", "상태"
        }


def test_write_csv_일치_row(tmp_path):
    results = [CompareResult("ad_A", 70, "uid1", 70, 0, "일치")]
    path = write_csv(results, tmp_path)
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["광고명"] == "ad_A"
    assert rows[0]["소재_할인율"] == "70"
    assert rows[0]["실제_최대_할인율"] == "70"
    assert rows[0]["오차"] == "0"
    assert rows[0]["상태"] == "일치"


def test_write_csv_불일치_row(tmp_path):
    results = [CompareResult("ad_B", 70, "uid2", 68, 2, "불일치")]
    path = write_csv(results, tmp_path)
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["상태"] == "불일치"
    assert rows[0]["오차"] == "2"


def test_write_csv_추출불가_row(tmp_path):
    results = [CompareResult("ad_C", None, None, None, None, "추출불가")]
    path = write_csv(results, tmp_path)
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["소재_할인율"] == "추출불가"
    assert rows[0]["상태"] == "추출불가"


def test_write_csv_multiple_rows(tmp_path):
    results = [
        CompareResult("ad_A", 70, "uid1", 70, 0, "일치"),
        CompareResult("ad_B", 70, "uid2", 68, 2, "불일치"),
    ]
    path = write_csv(results, tmp_path)
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/discount_checker/test_reporter.py -v
```

Expected: `ImportError`

- [ ] **Step 3: 구현 작성**

`tools/discount_checker/reporter.py`:

```python
import csv
import json
import urllib.request
from datetime import datetime
from pathlib import Path

from tools.discount_checker.comparator import CompareResult


def write_csv(results: list[CompareResult], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = output_dir / f"discount_check_{date_str}.csv"

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["검수일시", "광고명", "소재_할인율", "대표_UID", "실제_최대_할인율", "오차", "상태"]
        )
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for r in results:
            writer.writerow([
                now,
                r.ad_name,
                r.creative_discount if r.creative_discount is not None else "추출불가",
                r.representative_uid or "",
                r.actual_max_discount if r.actual_max_discount is not None else "",
                r.diff if r.diff is not None else "",
                r.status,
            ])
    return path


def send_slack(results: list[CompareResult], webhook_url: str) -> None:
    if not webhook_url:
        return
    mismatches = [r for r in results if r.status == "불일치"]
    for r in mismatches:
        text = (
            f"⚠️ [할인율 불일치] {r.ad_name}\n"
            f"소재: {r.creative_discount}% → 실제 최대: {r.actual_max_discount}% (오차 {r.diff:+d}%)\n"
            f"UID: {r.representative_uid}"
        )
        payload = json.dumps({"text": text}).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            print(f"[경고] Slack 알림 전송 실패: {e}")
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/discount_checker/test_reporter.py -v
```

Expected: 7 passed

- [ ] **Step 5: 커밋**

```bash
git add tools/discount_checker/reporter.py tests/discount_checker/test_reporter.py
git commit -m "feat: add CSV reporter and Slack notifier"
```

---

## Task 5: sheet_reader.py

**Files:**
- Create: `tools/discount_checker/sheet_reader.py`
- Create: `tests/discount_checker/test_sheet_reader.py`

- [ ] **Step 1: 테스트 작성**

`tests/discount_checker/test_sheet_reader.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from tools.discount_checker.sheet_reader import parse_sheets_url, _find_header_indices, _parse_uid_list


def test_parse_spreadsheet_id():
    url = "https://docs.google.com/spreadsheets/d/16kWSflx6xgn_VixO-tQoFylvJ2L85TdfX665MNFQw0A/edit#gid=288639799"
    sid, gid, range_str = parse_sheets_url(url)
    assert sid == "16kWSflx6xgn_VixO-tQoFylvJ2L85TdfX665MNFQw0A"


def test_parse_gid():
    url = "https://docs.google.com/spreadsheets/d/16kWSflx6xgn_VixO-tQoFylvJ2L85TdfX665MNFQw0A/edit#gid=288639799"
    sid, gid, range_str = parse_sheets_url(url)
    assert gid == "288639799"


def test_parse_range_from_fragment():
    url = "https://docs.google.com/spreadsheets/d/ABC/edit#gid=123&range=A1:Z100"
    sid, gid, range_str = parse_sheets_url(url)
    assert range_str == "A1:Z100"


def test_parse_no_range_returns_none():
    url = "https://docs.google.com/spreadsheets/d/ABC/edit#gid=123"
    sid, gid, range_str = parse_sheets_url(url)
    assert range_str is None


def test_invalid_url_raises():
    with pytest.raises(ValueError, match="Invalid Google Sheets URL"):
        parse_sheets_url("https://example.com/not-a-sheet")


def test_find_header_indices_success():
    rows = [
        [],
        ["", "캠페인", "광고명", "담당", "UID"],
        ["", "캠1", "ad_A", "담당자", "uid1, uid2"],
    ]
    ad_idx, uid_idx, header_row_idx = _find_header_indices(rows, "광고명", "UID")
    assert ad_idx == 2
    assert uid_idx == 4
    assert header_row_idx == 1


def test_find_header_indices_missing_ad_col():
    rows = [["캠페인", "그룹", "UID"]]
    with pytest.raises(ValueError, match="광고명"):
        _find_header_indices(rows, "광고명", "UID")


def test_find_header_indices_missing_uid_col():
    rows = [["광고명", "캠페인"]]
    with pytest.raises(ValueError, match="UID"):
        _find_header_indices(rows, "광고명", "UID")


def test_parse_uid_list_comma_separated():
    result = _parse_uid_list("4944027, 3825639, 3752602")
    assert result == ["4944027", "3825639", "3752602"]


def test_parse_uid_list_single():
    result = _parse_uid_list("5877083")
    assert result == ["5877083"]


def test_parse_uid_list_with_parentheses_in_note():
    # "3727165(껌정), 2384820(그린)" 형태 — 괄호 내용 제거 후 UID만
    result = _parse_uid_list("4167495, 3727165(껌정), 2384820(그린)")
    assert result == ["4167495", "3727165", "2384820"]
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/discount_checker/test_sheet_reader.py -v
```

Expected: `ImportError`

- [ ] **Step 3: 구현 작성**

`tools/discount_checker/sheet_reader.py`:

```python
import re
from urllib.parse import parse_qs

from google.oauth2 import service_account
from googleapiclient.discovery import build

from tools.discount_checker.comparator import AdRow

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def parse_sheets_url(url: str) -> tuple[str, str | None, str | None]:
    """Returns (spreadsheet_id, gid, range_str)."""
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not match:
        raise ValueError(f"Invalid Google Sheets URL: {url}")
    spreadsheet_id = match.group(1)

    fragment = url.split("#")[-1] if "#" in url else ""
    frag_params = parse_qs(fragment)
    gid = frag_params.get("gid", [None])[0]
    range_str = frag_params.get("range", [None])[0]
    return spreadsheet_id, gid, range_str


def _parse_uid_list(raw: str) -> list[str]:
    """'4944027, 3825639(메모)' → ['4944027', '3825639']"""
    parts = raw.split(",")
    uids = []
    for p in parts:
        p = p.strip()
        p = re.sub(r"\(.*?\)", "", p).strip()
        if p:
            uids.append(p)
    return uids


def _find_header_indices(
    rows: list[list[str]], ad_col: str, uid_col: str
) -> tuple[int, int, int]:
    """Returns (ad_col_index, uid_col_index, header_row_index)."""
    for row_idx, row in enumerate(rows):
        if ad_col in row:
            if uid_col not in row:
                raise ValueError(
                    f"'{uid_col}' 컬럼을 헤더에서 찾을 수 없습니다. 헤더: {row}"
                )
            return row.index(ad_col), row.index(uid_col), row_idx
    raise ValueError(
        f"'{ad_col}' 컬럼을 헤더에서 찾을 수 없습니다."
    )


def _gid_to_sheet_name(service, spreadsheet_id: str, gid: str) -> str:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in meta["sheets"]:
        if str(sheet["properties"]["sheetId"]) == gid:
            return sheet["properties"]["title"]
    raise ValueError(f"gid={gid} 에 해당하는 시트를 찾을 수 없습니다.")


def read_ad_rows(
    url: str,
    service_account_json: str,
    ad_col: str = "광고명",
    uid_col: str = "UID",
) -> list[AdRow]:
    creds = service_account.Credentials.from_service_account_file(
        service_account_json, scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=creds)

    spreadsheet_id, gid, range_str = parse_sheets_url(url)
    sheet_name = _gid_to_sheet_name(service, spreadsheet_id, gid) if gid else None

    if range_str and sheet_name:
        full_range = f"'{sheet_name}'!{range_str}"
    elif sheet_name:
        full_range = f"'{sheet_name}'"
    else:
        full_range = range_str

    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=full_range)
        .execute()
    )
    rows = result.get("values", [])
    if not rows:
        return []

    ad_idx, uid_idx, header_row_idx = _find_header_indices(rows, ad_col, uid_col)

    ad_rows = []
    for row in rows[header_row_idx + 1:]:
        ad_name = row[ad_idx].strip() if ad_idx < len(row) else ""
        uid_raw = row[uid_idx].strip() if uid_idx < len(row) else ""
        if not ad_name or not uid_raw:
            continue
        ad_rows.append(AdRow(ad_name=ad_name, uids=_parse_uid_list(uid_raw)))

    return ad_rows
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/discount_checker/test_sheet_reader.py -v
```

Expected: 11 passed

- [ ] **Step 5: 커밋**

```bash
git add tools/discount_checker/sheet_reader.py tests/discount_checker/test_sheet_reader.py
git commit -m "feat: add sheet_reader with URL parsing and header detection"
```

---

## Task 6: product_scraper.py

**Files:**
- Create: `tools/discount_checker/product_scraper.py`
- Create: `tests/discount_checker/test_product_scraper.py`

> **참고:** `_scrape_discount`의 CSS 선택자와 정규식은 무신사 페이지 실제 HTML 구조에 따라 조정이 필요할 수 있다. 첫 실행 후 실제 페이지에서 할인율 요소를 확인하고 선택자를 튜닝하라.

- [ ] **Step 1: 테스트 작성**

`tests/discount_checker/test_product_scraper.py`:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/discount_checker/test_product_scraper.py -v
```

Expected: `ImportError`

- [ ] **Step 3: 구현 작성**

`tools/discount_checker/product_scraper.py`:

```python
import re
from pathlib import Path
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
            if rate is not None:
                self._cache.set(cache_key, rate, ttl_seconds=CACHE_TTL)
            results[uid] = rate
        return results
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/discount_checker/test_product_scraper.py -v
```

Expected: 8 passed

- [ ] **Step 5: 커밋**

```bash
git add tools/discount_checker/product_scraper.py tests/discount_checker/test_product_scraper.py
git commit -m "feat: add product_scraper with Playwright and HTML discount parser"
```

---

## Task 7: image_analyzer.py

**Files:**
- Create: `tools/discount_checker/image_analyzer.py`
- Create: `tests/discount_checker/test_image_analyzer.py`

- [ ] **Step 1: 테스트 작성**

`tests/discount_checker/test_image_analyzer.py`:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/discount_checker/test_image_analyzer.py -v
```

Expected: `ImportError`

- [ ] **Step 3: 구현 작성**

`tools/discount_checker/image_analyzer.py`:

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/discount_checker/test_image_analyzer.py -v
```

Expected: 7 passed

- [ ] **Step 5: 커밋**

```bash
git add tools/discount_checker/image_analyzer.py tests/discount_checker/test_image_analyzer.py
git commit -m "feat: add image_analyzer with Claude Vision and image hash cache"
```

---

## Task 8: meta_client.py

**Files:**
- Create: `tools/discount_checker/meta_client.py`
- Create: `tests/discount_checker/test_meta_client.py`

- [ ] **Step 1: 테스트 작성**

`tests/discount_checker/test_meta_client.py`:

```python
from unittest.mock import patch, MagicMock
from tools.discount_checker.cache import Cache, CACHE_MISS
from tools.discount_checker.meta_client import MetaClient, _extract_image_url


def test_returns_none_when_no_ads_found(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    with patch("tools.discount_checker.meta_client.FacebookAdsApi"):
        with patch("tools.discount_checker.meta_client.AdAccount") as mock_account_cls:
            mock_account = MagicMock()
            mock_account_cls.return_value = mock_account
            mock_account.get_ads.return_value = []
            client = MetaClient("token", "act_123", cache)
            result = client.get_creative("ad_name_not_found")
    assert result is None


def test_returns_creative_id_and_image_url(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    with patch("tools.discount_checker.meta_client.FacebookAdsApi"), \
         patch("tools.discount_checker.meta_client.AdAccount") as mock_account_cls, \
         patch("tools.discount_checker.meta_client.AdCreative") as mock_creative_cls:

        mock_account = MagicMock()
        mock_account_cls.return_value = mock_account

        mock_ad = {"name": "test_ad", "creative": {"id": "cid_001"}}
        mock_account.get_ads.return_value = [mock_ad]

        mock_creative = MagicMock()
        mock_creative_cls.return_value.api_get.return_value = {
            "image_url": "http://example.com/img.jpg"
        }

        client = MetaClient("token", "act_123", cache)
        result = client.get_creative("test_ad")

    assert result == ("cid_001", "http://example.com/img.jpg")


def test_extract_image_url_prefers_image_url():
    creative_data = {"image_url": "http://img.jpg", "thumbnail_url": "http://thumb.jpg"}
    assert _extract_image_url(creative_data) == "http://img.jpg"


def test_extract_image_url_falls_back_to_thumbnail():
    creative_data = {"thumbnail_url": "http://thumb.jpg"}
    assert _extract_image_url(creative_data) == "http://thumb.jpg"


def test_extract_image_url_returns_none_when_missing():
    assert _extract_image_url({}) is None
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/discount_checker/test_meta_client.py -v
```

Expected: `ImportError`

- [ ] **Step 3: 구현 작성**

`tools/discount_checker/meta_client.py`:

```python
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.api import FacebookAdsApi

from tools.discount_checker.cache import Cache


def _extract_image_url(creative_data: dict) -> str | None:
    return creative_data.get("image_url") or creative_data.get("thumbnail_url")


class MetaClient:
    def __init__(self, access_token: str, ad_account_id: str, cache: Cache):
        FacebookAdsApi.init(access_token=access_token)
        self._account = AdAccount(ad_account_id)
        self._cache = cache

    def get_creative(self, ad_name: str) -> tuple[str, str] | None:
        """Returns (creative_id, image_url) or None if not found."""
        ads = self._account.get_ads(
            fields=["name", "creative"],
            params={
                "filtering": [{"field": "name", "operator": "EQUAL", "value": ad_name}]
            },
        )
        if not ads:
            return None

        creative_id = ads[0]["creative"]["id"]
        creative_data = AdCreative(creative_id).api_get(
            fields=["image_url", "thumbnail_url"]
        )
        image_url = _extract_image_url(creative_data)
        if not image_url:
            return None

        return creative_id, image_url
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/discount_checker/test_meta_client.py -v
```

Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
git add tools/discount_checker/meta_client.py tests/discount_checker/test_meta_client.py
git commit -m "feat: add meta_client for Meta Marketing API creative lookup"
```

---

## Task 9: config.py + check.py (CLI 진입점)

**Files:**
- Create: `tools/discount_checker/config.py`
- Create: `tools/discount_checker/check.py`

- [ ] **Step 1: config.py 작성**

`tools/discount_checker/config.py`:

```python
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

META_ACCESS_TOKEN: str = os.environ["META_ACCESS_TOKEN"]
META_AD_ACCOUNT_ID: str = os.environ["META_AD_ACCOUNT_ID"]
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
SLACK_WEBHOOK_URL: str = os.environ.get("SLACK_WEBHOOK_URL", "")
GOOGLE_SERVICE_ACCOUNT_JSON: str = os.environ.get(
    "GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json"
)

CACHE_PATH = Path("cache/discount_check_cache.json")
OUTPUT_DIR = Path("output")
```

- [ ] **Step 2: check.py 작성**

`tools/discount_checker/check.py`:

```python
import argparse
import sys

from tools.discount_checker import config
from tools.discount_checker.cache import Cache
from tools.discount_checker.comparator import CompareResult, compare
from tools.discount_checker.image_analyzer import ImageAnalyzer
from tools.discount_checker.meta_client import MetaClient
from tools.discount_checker.product_scraper import ProductScraper
from tools.discount_checker.reporter import send_slack, write_csv
from tools.discount_checker.sheet_reader import read_ad_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="광고 소재 할인율 검수")
    parser.add_argument("--sheet-url", required=True, help="Google Sheets URL")
    parser.add_argument("--ad-col", default="광고명", help="광고명 컬럼 헤더 (기본: 광고명)")
    parser.add_argument("--uid-col", default="UID", help="UID 컬럼 헤더 (기본: UID)")
    args = parser.parse_args()

    cache = Cache(config.CACHE_PATH)
    meta = MetaClient(config.META_ACCESS_TOKEN, config.META_AD_ACCOUNT_ID, cache)
    analyzer = ImageAnalyzer(config.ANTHROPIC_API_KEY, cache)
    scraper = ProductScraper(cache)

    try:
        ad_rows = read_ad_rows(
            args.sheet_url,
            config.GOOGLE_SERVICE_ACCOUNT_JSON,
            ad_col=args.ad_col,
            uid_col=args.uid_col,
        )
    except ValueError as e:
        print(f"[오류] {e}", file=sys.stderr)
        sys.exit(1)

    print(f"총 {len(ad_rows)}개 광고 검수 시작")
    results: list[CompareResult] = []

    for row in ad_rows:
        print(f"  처리 중: {row.ad_name}")
        creative = meta.get_creative(row.ad_name)
        if creative is None:
            results.append(
                CompareResult(row.ad_name, None, None, None, None, "조회실패")
            )
            continue

        creative_id, image_url = creative
        creative_discount = analyzer.extract_discount(creative_id, image_url)
        uid_discounts = scraper.get_max_discount(row.uids)
        results.append(compare(row.ad_name, creative_discount, uid_discounts))

    csv_path = write_csv(results, config.OUTPUT_DIR)
    print(f"\n결과 저장: {csv_path}")

    send_slack(results, config.SLACK_WEBHOOK_URL)

    mismatch_count = sum(1 for r in results if r.status == "불일치")
    print(f"완료: {len(results)}건 검수, {mismatch_count}건 불일치")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 전체 테스트 통과 확인**

```bash
pytest tests/discount_checker/ -v
```

Expected: 모든 테스트 통과

- [ ] **Step 4: 동작 확인 (실제 자격증명 필요)**

`.env` 파일에 실제 값이 있는 상태에서:

```bash
python -m tools.discount_checker.check \
  --sheet-url "https://docs.google.com/spreadsheets/d/16kWSflx6xgn_VixO-tQoFylvJ2L85TdfX665MNFQw0A/edit#gid=288639799" \
  --ad-col "광고명" \
  --uid-col "UID"
```

Expected:
```
총 N개 광고 검수 시작
  처리 중: 260420_PMKT_전사_상시_아울렛_1만원이하_CPC_FBDADCP4106
  ...
결과 저장: output/discount_check_2026-05-26.csv
완료: N건 검수, M건 불일치
```

> **무신사 스크래핑 튜닝:** 첫 실행 후 `output/*.csv` 에서 `실제_최대_할인율` 컬럼이 대부분 비어 있으면, Playwright 브라우저에서 `https://www.musinsa.com/products/{임의_UID}` 를 열어 실제 할인율 요소의 CSS 클래스를 확인하고 `product_scraper.py`의 `query_selector` 인자를 수정하라.

- [ ] **Step 5: 커밋**

```bash
git add tools/discount_checker/config.py tools/discount_checker/check.py
git commit -m "feat: add config and CLI entry point for discount_checker"
```

---

## 전체 테스트 실행

```bash
pytest tests/discount_checker/ -v --tb=short
```

Expected: 39 passed (캐시 6 + 비교 8 + 리포터 7 + 시트리더 11 + 스크래퍼 8 + 이미지 7 + 메타 5 — 실제 수는 구현에 따라 다를 수 있음)
