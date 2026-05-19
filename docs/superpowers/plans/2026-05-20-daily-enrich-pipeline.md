# Daily Enrich Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 데일리 raw CSV를 받아 캠페인명을 파싱(brand, 판매채널, 광고목표, 소재유형, 타겟구분, 기획전명)하고 weeknum/연월을 추가한 뒤 Google Sheets 오버라이드 인덱스를 적용하여 enriched CSV를 `data/output/`에 저장한다.

**Architecture:** `캠페인 이름`을 `_` 분리 + regex로 1차 파싱 → 복합키(`캠페인 이름` + `광고 세트 이름` + `광고 이름`) 기준 Google Sheets 인덱스 left join으로 오버라이드 적용 → 파싱 실패 행은 인덱스 시트에 자동 추가(gspread). 읽기는 기존 프로젝트 패턴(CSV export URL + requests)을 그대로 따름.

**Tech Stack:** Python 3.11+, pandas, requests, gspread, google-auth, pytest

---

## 파일 구조

```
tools/enrich_daily/
├── __init__.py          # 비어 있음
├── config.py            # SPREADSHEET_ID, GID, 경로 상수
├── parser.py            # 캠페인명 regex 파싱 순수 함수
├── sheets_client.py     # Sheets 읽기(requests) + 쓰기(gspread)
└── enrich.py            # 파이프라인 조립 + CLI

tests/enrich_daily/
├── __init__.py
├── test_parser.py
├── test_sheets_client.py
└── test_enrich.py
```

---

## Google Sheets 인덱스 시트 양식 (`ad_index`)

| 캠페인 이름 | 광고 세트 이름 | 광고 이름 | brand | 판매채널 | 광고목표 | 소재유형 | 타겟구분 | 기획전명 | 비고 |
|------------|--------------|---------|-------|---------|---------|---------|---------|---------|-----|

- 3개 복합키로 join. 오버라이드 컬럼은 비워두면 자동 파싱값 사용.
- 파싱 실패 행: 3개 키만 자동 추가됨 → 사람이 나머지 채우기.

---

## Task 1: Scaffold + config.py

**Files:**
- Create: `tools/__init__.py`
- Create: `tools/enrich_daily/__init__.py`
- Create: `tools/enrich_daily/config.py`
- Create: `tests/enrich_daily/__init__.py`

- [ ] **Step 1: 디렉토리 및 빈 파일 생성**

```bash
mkdir -p tools/enrich_daily tests/enrich_daily
touch tools/__init__.py tools/enrich_daily/__init__.py tests/enrich_daily/__init__.py
```

- [ ] **Step 2: config.py 작성**

```python
# tools/enrich_daily/config.py
SPREADSHEET_ID = "YOUR_SPREADSHEET_ID"   # Google Sheets 스프레드시트 ID로 교체
INDEX_GID = "0"                           # ad_index 시트의 gid
INDEX_SHEET_NAME = "ad_index"             # gspread용 시트 이름 (쓰기 시 사용)
CREDS_PATH = r"C:\Users\MADUP\.claude\google-service-account.json"
OUTPUT_DIR = "data/output"
```

- [ ] **Step 3: 의존성 확인**

```bash
pip install gspread google-auth pandas requests pytest
```

- [ ] **Step 4: Commit**

```bash
git add tools/ tests/enrich_daily/__init__.py
git commit -m "feat: scaffold enrich_daily tool"
```

---

## Task 2: parser.py (캠페인명 파싱)

**Files:**
- Create: `tools/enrich_daily/parser.py`
- Create: `tests/enrich_daily/test_parser.py`

캠페인명 구조: `26년 4월_잔스포츠_[무신사]하프파인트X뷰티 콜라보_전환_컬렉션_잠재고객/리타겟`
→ `_` 분리 시 `[0]=연도, [1]=brand, [2]=[채널]기획전명, [3]=광고목표, [4]=소재유형, [5+]=타겟구분`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/enrich_daily/test_parser.py
import pytest
from tools.enrich_daily.parser import parse_campaign_name, PARSED_COLS

NORMAL = "26년 4월_잔스포츠_[무신사]하프파인트X뷰티 콜라보_전환_컬렉션_잠재고객/리타겟"
ALWAYS_ON = "26년 4월_잔스포츠_[무신사]월별 상시 광고_전환_카탈로그_잠재고객/리타겟"
NO_CHANNEL = "26년 4월_잔스포츠_하프파인트X뷰티 콜라보_전환_컬렉션_잠재고객"
TOO_SHORT = "26년 4월_잔스포츠_뭔가"


def test_parse_normal_campaign():
    result = parse_campaign_name(NORMAL)
    assert result["brand"] == "잔스포츠"
    assert result["판매채널"] == "무신사"
    assert result["기획전명"] == "하프파인트X뷰티 콜라보"
    assert result["광고목표"] == "전환"
    assert result["소재유형"] == "컬렉션"
    assert result["타겟구분"] == "잠재고객/리타겟"


def test_parse_always_on_campaign():
    result = parse_campaign_name(ALWAYS_ON)
    assert result["brand"] == "잔스포츠"
    assert result["판매채널"] == "무신사"
    assert result["기획전명"] == "월별 상시 광고"
    assert result["소재유형"] == "카탈로그"


def test_parse_no_channel_bracket_returns_empty_channel():
    result = parse_campaign_name(NO_CHANNEL)
    assert result["판매채널"] == ""
    assert result["기획전명"] == "하프파인트X뷰티 콜라보"


def test_parse_too_short_returns_empty_dict():
    result = parse_campaign_name(TOO_SHORT)
    assert result == {}


def test_parsed_cols_constant():
    assert PARSED_COLS == ["brand", "판매채널", "광고목표", "소재유형", "타겟구분", "기획전명"]
```

- [ ] **Step 2: 테스트 실행 → FAIL 확인**

```bash
pytest tests/enrich_daily/test_parser.py -v
```
Expected: ImportError 또는 5개 FAIL

- [ ] **Step 3: parser.py 구현**

```python
# tools/enrich_daily/parser.py
import re

PARSED_COLS = ["brand", "판매채널", "광고목표", "소재유형", "타겟구분", "기획전명"]
_CHANNEL_RE = re.compile(r"^\[([^\]]+)\](.*)")


def parse_campaign_name(name: str) -> dict[str, str]:
    """캠페인명에서 6개 컬럼 추출. 파싱 불가 시 빈 dict 반환."""
    parts = name.split("_")
    if len(parts) < 6:
        return {}

    channel_event = parts[2]
    ch_match = _CHANNEL_RE.match(channel_event)

    return {
        "brand": parts[1].strip(),
        "판매채널": ch_match.group(1).strip() if ch_match else "",
        "기획전명": ch_match.group(2).strip() if ch_match else channel_event.strip(),
        "광고목표": parts[3].strip(),
        "소재유형": parts[4].strip(),
        "타겟구분": "_".join(parts[5:]).strip(),
    }
```

- [ ] **Step 4: 테스트 실행 → PASS 확인**

```bash
pytest tests/enrich_daily/test_parser.py -v
```
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add tools/enrich_daily/parser.py tests/enrich_daily/test_parser.py
git commit -m "feat: add campaign name parser"
```

---

## Task 3: sheets_client.py — 읽기 (load_index)

**Files:**
- Create: `tools/enrich_daily/sheets_client.py`
- Create: `tests/enrich_daily/test_sheets_client.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/enrich_daily/test_sheets_client.py
from unittest.mock import patch, MagicMock
import pandas as pd
from tools.enrich_daily.sheets_client import load_index, COMPOSITE_KEYS, OVERRIDE_COLS

INDEX_CSV = """캠페인 이름,광고 세트 이름,광고 이름,brand,판매채널,광고목표,소재유형,타겟구분,기획전명,비고
캠페인A,세트A,광고A,잔스포츠,무신사,전환,컬렉션,잠재고객,하프파인트 콜라보,수동입력
캠페인B,세트B,광고B,,,,,,, 
"""

MINIMAL_CSV = """캠페인 이름,광고 세트 이름,광고 이름
캠페인C,세트C,광고C
"""


def test_load_index_returns_dataframe():
    with patch("tools.enrich_daily.sheets_client.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=INDEX_CSV)
        mock_get.return_value.raise_for_status = MagicMock()
        df = load_index("FAKE_ID", "0")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2


def test_load_index_fills_missing_override_cols():
    with patch("tools.enrich_daily.sheets_client.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=MINIMAL_CSV)
        mock_get.return_value.raise_for_status = MagicMock()
        df = load_index("FAKE_ID", "0")
    for col in OVERRIDE_COLS:
        assert col in df.columns
        assert df[col].iloc[0] == ""


def test_composite_keys_and_override_cols_constants():
    assert COMPOSITE_KEYS == ["캠페인 이름", "광고 세트 이름", "광고 이름"]
    assert OVERRIDE_COLS == ["brand", "판매채널", "광고목표", "소재유형", "타겟구분", "기획전명"]
```

- [ ] **Step 2: 테스트 실행 → FAIL 확인**

```bash
pytest tests/enrich_daily/test_sheets_client.py -v
```
Expected: ImportError 또는 3 FAIL

- [ ] **Step 3: sheets_client.py 구현 (읽기 부분)**

```python
# tools/enrich_daily/sheets_client.py
import io
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

COMPOSITE_KEYS = ["캠페인 이름", "광고 세트 이름", "광고 이름"]
OVERRIDE_COLS = ["brand", "판매채널", "광고목표", "소재유형", "타겟구분", "기획전명"]
_ALL_COLS = COMPOSITE_KEYS + OVERRIDE_COLS + ["비고"]
_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def load_index(spreadsheet_id: str, gid: str) -> pd.DataFrame:
    """Google Sheets ad_index를 DataFrame으로 읽어옴 (CSV export 방식)."""
    url = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        f"/export?format=csv&gid={gid}"
    )
    resp = requests.get(url, timeout=10)
    resp.encoding = "utf-8"
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text), dtype=str).fillna("")
    for col in _ALL_COLS:
        if col not in df.columns:
            df[col] = ""
    return df
```

- [ ] **Step 4: 테스트 실행 → PASS 확인**

```bash
pytest tests/enrich_daily/test_sheets_client.py -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add tools/enrich_daily/sheets_client.py tests/enrich_daily/test_sheets_client.py
git commit -m "feat: add sheets index reader"
```

---

## Task 4: sheets_client.py — 쓰기 (append_missing_rows)

**Files:**
- Modify: `tools/enrich_daily/sheets_client.py`
- Modify: `tests/enrich_daily/test_sheets_client.py`

- [ ] **Step 1: 실패하는 테스트 추가**

```python
# tests/enrich_daily/test_sheets_client.py 에 추가
from unittest.mock import patch, MagicMock, call
from tools.enrich_daily.sheets_client import append_missing_rows

def test_append_missing_rows_skips_duplicates():
    mock_ws = MagicMock()
    # 헤더 + 기존 1행
    mock_ws.get_all_values.return_value = [
        ["캠페인 이름", "광고 세트 이름", "광고 이름", "brand", "판매채널", "광고목표", "소재유형", "타겟구분", "기획전명", "비고"],
        ["캠페인A", "세트A", "광고A", "", "", "", "", "", "", ""],
    ]
    mock_gc = MagicMock()
    mock_gc.open_by_key.return_value.worksheet.return_value = mock_ws

    with patch("tools.enrich_daily.sheets_client.gspread.authorize", return_value=mock_gc), \
         patch("tools.enrich_daily.sheets_client.Credentials.from_service_account_file"):
        append_missing_rows(
            spreadsheet_id="FAKE",
            sheet_name="ad_index",
            creds_path="fake.json",
            missing_rows=[
                {"캠페인 이름": "캠페인A", "광고 세트 이름": "세트A", "광고 이름": "광고A"},  # 중복
                {"캠페인 이름": "캠페인B", "광고 세트 이름": "세트B", "광고 이름": "광고B"},  # 신규
            ],
        )

    mock_ws.append_rows.assert_called_once()
    appended = mock_ws.append_rows.call_args[0][0]
    assert len(appended) == 1
    assert appended[0][0] == "캠페인B"


def test_append_missing_rows_does_nothing_when_empty():
    with patch("tools.enrich_daily.sheets_client.gspread.authorize") as mock_auth:
        append_missing_rows("FAKE", "ad_index", "fake.json", [])
    mock_auth.assert_not_called()
```

- [ ] **Step 2: 테스트 실행 → FAIL 확인**

```bash
pytest tests/enrich_daily/test_sheets_client.py::test_append_missing_rows_skips_duplicates tests/enrich_daily/test_sheets_client.py::test_append_missing_rows_does_nothing_when_empty -v
```
Expected: 2 FAIL

- [ ] **Step 3: append_missing_rows 구현 추가**

```python
# tools/enrich_daily/sheets_client.py 에 추가

def append_missing_rows(
    spreadsheet_id: str,
    sheet_name: str,
    creds_path: str,
    missing_rows: list[dict],
) -> None:
    """파싱 실패 행의 3개 키를 Sheets 인덱스에 추가 (기존 키 중복 제외)."""
    if not missing_rows:
        return

    creds = Credentials.from_service_account_file(creds_path, scopes=_SCOPES)
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(spreadsheet_id).worksheet(sheet_name)

    all_vals = ws.get_all_values()
    if not all_vals:
        return
    header = all_vals[0]

    key_indices = [header.index(k) for k in COMPOSITE_KEYS if k in header]
    existing_keys: set[tuple] = set(
        tuple(row[i] for i in key_indices)
        for row in all_vals[1:]
        if len(row) > max(key_indices, default=-1)
    )

    to_append = []
    for row_dict in missing_rows:
        key = tuple(row_dict.get(k, "") for k in COMPOSITE_KEYS)
        if key not in existing_keys:
            new_row = [row_dict.get(col, "") for col in header]
            to_append.append(new_row)
            existing_keys.add(key)

    if to_append:
        ws.append_rows(to_append, value_input_option="USER_ENTERED")
```

- [ ] **Step 4: 테스트 실행 → PASS 확인**

```bash
pytest tests/enrich_daily/test_sheets_client.py -v
```
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add tools/enrich_daily/sheets_client.py tests/enrich_daily/test_sheets_client.py
git commit -m "feat: add sheets index auto-append for parse failures"
```

---

## Task 5: enrich.py — 파이프라인 조립

**Files:**
- Create: `tools/enrich_daily/enrich.py`
- Create: `tests/enrich_daily/test_enrich.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/enrich_daily/test_enrich.py
import io
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from tools.enrich_daily.enrich import add_date_columns, add_parsed_columns, apply_overrides, get_parse_failures

RAW_ROWS = [
    {
        "연월": "2026-05",
        "날짜": "2026-05-05",
        "media": "메타",
        "캠페인 이름": "26년 4월_잔스포츠_[무신사]하프파인트X뷰티 콜라보_전환_컬렉션_잠재고객/리타겟",
        "광고 세트 이름": "컬렉션_[무신사]하프파인트X뷰티콜라보_잠재고객_1865+_남여",
        "광고 이름": "컬렉션6",
    },
    {
        "연월": "2026-05",
        "날짜": "2026-05-05",
        "media": "메타",
        "캠페인 이름": "파싱실패_이름",  # 6 파트 미만 → 파싱 실패
        "광고 세트 이름": "세트X",
        "광고 이름": "광고X",
    },
]


@pytest.fixture
def raw_df():
    return pd.DataFrame(RAW_ROWS)


def test_add_date_columns(raw_df):
    df = add_date_columns(raw_df)
    assert df["weeknum"].iloc[0] == 19   # 2026-05-05는 ISO week 19 (월요일 기준)
    assert df["연월"].iloc[0] == "2026-05"


def test_add_parsed_columns(raw_df):
    df = add_parsed_columns(raw_df)
    assert df["brand"].iloc[0] == "잔스포츠"
    assert df["판매채널"].iloc[0] == "무신사"
    assert df["광고목표"].iloc[0] == "전환"
    assert df["소재유형"].iloc[0] == "컬렉션"
    assert df["타겟구분"].iloc[0] == "잠재고객/리타겟"
    assert df["기획전명"].iloc[0] == "하프파인트X뷰티 콜라보"
    # 파싱 실패 행은 빈 문자열
    assert df["brand"].iloc[1] == ""


def test_apply_overrides(raw_df):
    df = add_parsed_columns(raw_df)
    index_df = pd.DataFrame([{
        "캠페인 이름": "26년 4월_잔스포츠_[무신사]하프파인트X뷰티 콜라보_전환_컬렉션_잠재고객/리타겟",
        "광고 세트 이름": "컬렉션_[무신사]하프파인트X뷰티콜라보_잠재고객_1865+_남여",
        "광고 이름": "컬렉션6",
        "brand": "JanSport",   # 오버라이드
        "판매채널": "",         # 비어있음 → 파싱값 유지
        "광고목표": "", "소재유형": "", "타겟구분": "", "기획전명": "",
    }])
    result = apply_overrides(df, index_df)
    assert result["brand"].iloc[0] == "JanSport"
    assert result["판매채널"].iloc[0] == "무신사"   # 빈 오버라이드 → 파싱값 유지


def test_get_parse_failures(raw_df):
    df = add_parsed_columns(raw_df)
    failures = get_parse_failures(df)
    assert len(failures) == 1
    assert failures[0]["캠페인 이름"] == "파싱실패_이름"
    assert failures[0]["광고 이름"] == "광고X"
```

- [ ] **Step 2: 테스트 실행 → FAIL 확인**

```bash
pytest tests/enrich_daily/test_enrich.py -v
```
Expected: ImportError 또는 4 FAIL

- [ ] **Step 3: enrich.py 구현**

```python
# tools/enrich_daily/enrich.py
import sys
from pathlib import Path
import pandas as pd

from .config import SPREADSHEET_ID, INDEX_GID, INDEX_SHEET_NAME, CREDS_PATH, OUTPUT_DIR
from .parser import parse_campaign_name, PARSED_COLS
from .sheets_client import load_index, append_missing_rows, COMPOSITE_KEYS, OVERRIDE_COLS


def add_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    dates = pd.to_datetime(df["날짜"])
    df["weeknum"] = dates.dt.isocalendar().week.astype(int)
    df["연월"] = dates.dt.strftime("%Y-%m")
    return df


def add_parsed_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    parsed = df["캠페인 이름"].apply(parse_campaign_name)
    for col in PARSED_COLS:
        df[col] = parsed.apply(lambda d, c=col: d.get(c, ""))
    return df


def apply_overrides(df: pd.DataFrame, index_df: pd.DataFrame) -> pd.DataFrame:
    if index_df.empty:
        return df
    override_cols_present = [c for c in OVERRIDE_COLS if c in index_df.columns]
    index_subset = index_df[COMPOSITE_KEYS + override_cols_present].copy()
    merged = df.merge(index_subset, on=COMPOSITE_KEYS, how="left", suffixes=("", "_ov"))
    for col in override_cols_present:
        ov = f"{col}_ov"
        if ov in merged.columns:
            mask = merged[ov].notna() & (merged[ov] != "")
            merged[col] = merged[ov].where(mask, merged[col])
            merged.drop(columns=[ov], inplace=True)
    return merged


def get_parse_failures(df: pd.DataFrame) -> list[dict]:
    failed = df[df["brand"] == ""]
    return failed[COMPOSITE_KEYS].drop_duplicates().to_dict("records")


def enrich(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig")
    df = add_date_columns(df)
    df = add_parsed_columns(df)

    index_df = load_index(SPREADSHEET_ID, INDEX_GID)
    df = apply_overrides(df, index_df)

    failures = get_parse_failures(df)
    if failures:
        append_missing_rows(SPREADSHEET_ID, INDEX_SHEET_NAME, CREDS_PATH, failures)
        print(f"[INFO] {len(failures)}건 파싱 실패 → Sheets 인덱스에 추가됨")

    new_cols = ["weeknum", "연월"] + PARSED_COLS
    original_cols = [c for c in df.columns if c not in new_cols]
    return df[new_cols + original_cols]


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m tools.enrich_daily.enrich <csv_path>")
        sys.exit(1)

    csv_path = sys.argv[1]
    output_path = Path(OUTPUT_DIR) / f"enriched_{Path(csv_path).stem}.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = enrich(csv_path)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"[DONE] {output_path} ({len(df):,}행)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 테스트 실행 → PASS 확인**

```bash
pytest tests/enrich_daily/test_enrich.py -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add tools/enrich_daily/enrich.py tests/enrich_daily/test_enrich.py
git commit -m "feat: add enrich pipeline with override and failure tracking"
```

---

## Task 6: 전체 테스트 + 실제 실행 검증

**Files:**
- No new files

- [ ] **Step 1: 전체 테스트 실행**

```bash
pytest tests/enrich_daily/ -v
```
Expected: 12 passed (모든 테스트 통과)

- [ ] **Step 2: config.py에 실제 SPREADSHEET_ID 입력**

`tools/enrich_daily/config.py`의 `SPREADSHEET_ID`를 실제 Google Sheets ID로 교체. Google Sheets에 `ad_index` 시트가 없으면 시트를 생성하고 다음 헤더 행 추가:

```
캠페인 이름 | 광고 세트 이름 | 광고 이름 | brand | 판매채널 | 광고목표 | 소재유형 | 타겟구분 | 기획전명 | 비고
```

`INDEX_GID`는 해당 시트 URL의 `gid=` 값으로 교체.

- [ ] **Step 3: 실제 CSV로 실행**

```bash
python -m tools.enrich_daily.enrich "C:\Users\MADUP\Downloads\데일리raw_2026-05-01_2026-05-18.csv"
```

Expected 출력:
```
[DONE] data/output/enriched_데일리raw_2026-05-01_2026-05-18.csv (XXXX행)
```

- [ ] **Step 4: 결과 확인**

```python
import pandas as pd
df = pd.read_csv("data/output/enriched_데일리raw_2026-05-01_2026-05-18.csv", encoding="utf-8-sig")
print(df[["weeknum", "연월", "brand", "판매채널", "광고목표", "소재유형", "타겟구분", "기획전명"]].head(10))
print(f"파싱 성공률: {(df['brand'] != '').mean():.1%}")
```

- [ ] **Step 5: Final commit**

```bash
git add tools/enrich_daily/config.py
git commit -m "feat: complete daily enrich pipeline"
```

---

## 실행 방법 (완성 후)

```bash
# 기본 실행
python -m tools.enrich_daily.enrich <csv_파일경로>

# 출력: data/output/enriched_<원본파일명>.csv
# 파싱 실패 행: Google Sheets ad_index에 자동 추가 → 수동으로 채우기
```
