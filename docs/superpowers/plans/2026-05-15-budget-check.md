# Budget Check App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 엑스퍼트 RD 파일 + Meta/카카오 API 소진액을 Google Sheets 예산 플랜과 비교해 과소진/미소진을 한눈에 보여주고 슬랙으로 발송하는 팀 공용 Streamlit 앱.

**Architecture:** `budget_check/` 디렉토리를 신규 독립 앱으로 구성. `loaders/` 는 각 데이터소스 수집, `logic/` 은 비교 계산만 담당하며 서로 의존하지 않음. `app.py` 가 두 레이어를 조합해 UI를 구성.

**Tech Stack:** Python 3.11+, Streamlit, pandas, requests, pytest

---

## 파일 맵

| 파일 | 역할 |
|------|------|
| `budget_check/app.py` | Streamlit UI, 데이터 수집·계산 조합 |
| `budget_check/loaders/rd_loader.py` | 업로드된 RD CSV 파싱, 날짜 필터, 매체+캠페인+그룹 집계 |
| `budget_check/loaders/meta_loader.py` | Meta Marketing API → 캠페인+adset별 소진액 |
| `budget_check/loaders/kakao_loader.py` | 카카오 모먼트 API → 캠페인+그룹별 소진액 |
| `budget_check/loaders/sheets_loader.py` | Google Sheets URL → CSV export → 일별 예산 플랜 DataFrame |
| `budget_check/logic/validator.py` | RD 소진 vs API 소진 비교, 상태 판정 |
| `budget_check/logic/budget_checker.py` | API 소진 vs 예산 플랜 비교, 과소진/미소진 판정 |
| `budget_check/slack_sender.py` | 결과 DataFrame → Slack Incoming Webhook POST |
| `budget_check/requirements.txt` | 의존성 목록 |
| `budget_check/.streamlit/secrets.toml` | 로컬 전용 API 키 (git 제외) |
| `tests/budget_check/test_rd_loader.py` | rd_loader 단위 테스트 |
| `tests/budget_check/test_sheets_loader.py` | sheets_loader 단위 테스트 |
| `tests/budget_check/test_validator.py` | validator 단위 테스트 |
| `tests/budget_check/test_budget_checker.py` | budget_checker 단위 테스트 |
| `tests/budget_check/test_slack_sender.py` | slack_sender 단위 테스트 |

---

## Task 1: 프로젝트 뼈대 세팅

**Files:**
- Create: `budget_check/app.py`
- Create: `budget_check/loaders/__init__.py`
- Create: `budget_check/logic/__init__.py`
- Create: `budget_check/requirements.txt`
- Create: `budget_check/.streamlit/secrets.toml`
- Create: `tests/budget_check/__init__.py`
- Modify: `.gitignore`

- [ ] **Step 1: 디렉토리 구조 생성**

```bash
mkdir -p budget_check/loaders budget_check/logic budget_check/.streamlit
mkdir -p tests/budget_check
touch budget_check/loaders/__init__.py budget_check/logic/__init__.py
touch tests/budget_check/__init__.py
```

- [ ] **Step 2: requirements.txt 작성**

`budget_check/requirements.txt`:
```
streamlit>=1.33.0
pandas>=2.0.0
requests>=2.31.0
pytest>=8.0.0
```

- [ ] **Step 3: secrets.toml 작성 (로컬 테스트용 더미값)**

`budget_check/.streamlit/secrets.toml`:
```toml
META_ACCESS_TOKEN = "dummy"
META_AD_ACCOUNT_ID = "dummy"
KAKAO_ACCESS_TOKEN = "dummy"
KAKAO_AD_ACCOUNT_ID = "dummy"
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/dummy"
```

- [ ] **Step 4: .gitignore에 secrets 추가**

기존 `.gitignore` 에 아래 줄 추가:
```
budget_check/.streamlit/secrets.toml
```

- [ ] **Step 5: app.py 빈 뼈대 작성**

`budget_check/app.py`:
```python
import streamlit as st

st.set_page_config(page_title="예산 점검", page_icon="📊", layout="wide")
st.title("📊 예산 점검")
st.info("구현 중입니다.")
```

- [ ] **Step 6: 실행 확인**

```bash
cd budget_check
streamlit run app.py
```
Expected: 브라우저에서 "📊 예산 점검" 타이틀과 "구현 중입니다." 메시지 표시

- [ ] **Step 7: 커밋**

```bash
git add budget_check/ tests/budget_check/ .gitignore
git commit -m "feat: scaffold budget_check app structure"
```

---

## Task 2: RD 로더

**Files:**
- Create: `budget_check/loaders/rd_loader.py`
- Create: `tests/budget_check/test_rd_loader.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/budget_check/test_rd_loader.py`:
```python
import io
import pandas as pd
from budget_check.loaders.rd_loader import load_rd

RD_CSV = """일,광고주 이름,캠페인 이름,광고 그룹 이름,소재명,노출,클릭,비용 (KRW),매체
2026-05-15,무신사,캠페인A,그룹1,소재X,1000,50,500000,Facebook
2026-05-15,무신사,캠페인A,그룹1,소재Y,500,20,200000,Facebook
2026-05-15,무신사,캠페인B,그룹2,소재Z,2000,80,800000,카카오
2026-05-14,무신사,캠페인A,그룹1,소재X,900,45,450000,Facebook
"""

def test_load_rd_filters_by_date():
    df = load_rd(io.StringIO(RD_CSV), date="2026-05-15")
    assert len(df) == 3  # 매체+캠페인+그룹 기준 집계 후 3행

def test_load_rd_aggregates_spend():
    df = load_rd(io.StringIO(RD_CSV), date="2026-05-15")
    row = df[(df["매체"] == "Facebook") & (df["캠페인"] == "캠페인A") & (df["그룹"] == "그룹1")]
    assert row["rd_소진"].iloc[0] == 700000  # 500000 + 200000

def test_load_rd_returns_expected_columns():
    df = load_rd(io.StringIO(RD_CSV), date="2026-05-15")
    assert list(df.columns) == ["매체", "캠페인", "그룹", "rd_소진"]

def test_load_rd_empty_when_date_not_found():
    df = load_rd(io.StringIO(RD_CSV), date="2026-05-01")
    assert df.empty
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd budget_check && python -m pytest ../tests/budget_check/test_rd_loader.py -v
```
Expected: `ModuleNotFoundError: No module named 'budget_check'`

- [ ] **Step 3: rd_loader.py 구현**

`budget_check/loaders/rd_loader.py`:
```python
import pandas as pd
from typing import Union
import io


def load_rd(source: Union[str, io.StringIO], date: str) -> pd.DataFrame:
    """RD CSV를 읽어 지정 날짜의 매체+캠페인+그룹별 소진액 DataFrame 반환."""
    df = pd.read_csv(source, encoding="utf-8-sig")

    df["일"] = pd.to_datetime(df["일"]).dt.strftime("%Y-%m-%d")
    df = df[df["일"] == date]

    if df.empty:
        return pd.DataFrame(columns=["매체", "캠페인", "그룹", "rd_소진"])

    # 컬럼명 정규화: '비용 (KRW)' 또는 '비용' 둘 다 허용
    spend_col = "비용 (KRW)" if "비용 (KRW)" in df.columns else "비용"

    result = (
        df.groupby(["매체", "캠페인 이름", "광고 그룹 이름"])[spend_col]
        .sum()
        .reset_index()
        .rename(columns={"캠페인 이름": "캠페인", "광고 그룹 이름": "그룹", spend_col: "rd_소진"})
    )
    return result[["매체", "캠페인", "그룹", "rd_소진"]]
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd budget_check && python -m pytest ../tests/budget_check/test_rd_loader.py -v
```
Expected: 4 tests PASSED

- [ ] **Step 5: 커밋**

```bash
git add budget_check/loaders/rd_loader.py tests/budget_check/test_rd_loader.py
git commit -m "feat: add RD CSV loader with date filter and spend aggregation"
```

---

## Task 3: Google Sheets 로더

**Files:**
- Create: `budget_check/loaders/sheets_loader.py`
- Create: `tests/budget_check/test_sheets_loader.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/budget_check/test_sheets_loader.py`:
```python
from unittest.mock import patch, MagicMock
import pandas as pd
import io
from budget_check.loaders.sheets_loader import parse_sheets_url, load_budget_plan

def test_parse_sheets_url_extracts_id_and_gid():
    url = "https://docs.google.com/spreadsheets/d/1FvRdm-E8kxJy/edit?gid=1367713947#gid=1367713947"
    sheet_id, gid = parse_sheets_url(url)
    assert sheet_id == "1FvRdm-E8kxJy"
    assert gid == "1367713947"

def test_parse_sheets_url_no_gid_defaults_to_zero():
    url = "https://docs.google.com/spreadsheets/d/1FvRdm-E8kxJy/edit"
    sheet_id, gid = parse_sheets_url(url)
    assert sheet_id == "1FvRdm-E8kxJy"
    assert gid == "0"

PLAN_CSV = """날짜,매체,캠페인,그룹,일예산
2026-05-15,Meta,캠페인A,그룹1,1200000
2026-05-15,Kakao,캠페인B,그룹2,400000
2026-05-14,Meta,캠페인A,그룹1,1000000
"""

def test_load_budget_plan_filters_by_date():
    with patch("budget_check.loaders.sheets_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=PLAN_CSV)
        df = load_budget_plan("https://docs.google.com/spreadsheets/d/FAKE/edit?gid=0", date="2026-05-15")
    assert len(df) == 2

def test_load_budget_plan_returns_expected_columns():
    with patch("budget_check.loaders.sheets_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=PLAN_CSV)
        df = load_budget_plan("https://docs.google.com/spreadsheets/d/FAKE/edit?gid=0", date="2026-05-15")
    assert list(df.columns) == ["매체", "캠페인", "그룹", "일예산"]
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd budget_check && python -m pytest ../tests/budget_check/test_sheets_loader.py -v
```
Expected: `ImportError`

- [ ] **Step 3: sheets_loader.py 구현**

`budget_check/loaders/sheets_loader.py`:
```python
import re
import io
import requests
import pandas as pd


def parse_sheets_url(url: str) -> tuple[str, str]:
    """Google Sheets URL에서 spreadsheet ID와 gid 추출."""
    match = re.search(r"/spreadsheets/d/([^/]+)", url)
    if not match:
        raise ValueError(f"유효한 Google Sheets URL이 아닙니다: {url}")
    sheet_id = match.group(1)

    gid_match = re.search(r"gid=(\d+)", url)
    gid = gid_match.group(1) if gid_match else "0"
    return sheet_id, gid


def load_budget_plan(url: str, date: str) -> pd.DataFrame:
    """Google Sheets URL에서 예산 플랜을 읽어 지정 날짜 행만 반환."""
    sheet_id, gid = parse_sheets_url(url)
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

    resp = requests.get(export_url, timeout=10)
    resp.raise_for_status()

    df = pd.read_csv(io.StringIO(resp.text))
    df["날짜"] = pd.to_datetime(df["날짜"]).dt.strftime("%Y-%m-%d")
    df = df[df["날짜"] == date]

    if df.empty:
        return pd.DataFrame(columns=["매체", "캠페인", "그룹", "일예산"])

    return df[["매체", "캠페인", "그룹", "일예산"]].reset_index(drop=True)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd budget_check && python -m pytest ../tests/budget_check/test_sheets_loader.py -v
```
Expected: 4 tests PASSED

- [ ] **Step 5: 커밋**

```bash
git add budget_check/loaders/sheets_loader.py tests/budget_check/test_sheets_loader.py
git commit -m "feat: add Google Sheets budget plan loader"
```

---

## Task 4: Meta API 로더

**Files:**
- Create: `budget_check/loaders/meta_loader.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/budget_check/test_meta_loader.py`:
```python
from unittest.mock import patch, MagicMock
import pandas as pd
from budget_check.loaders.meta_loader import fetch_meta_spend

META_RESPONSE = {
    "data": [
        {"campaign_name": "캠페인A", "adset_name": "그룹1", "spend": "998.00"},
        {"campaign_name": "캠페인C", "adset_name": "그룹3", "spend": "300.00"},
    ],
    "paging": {}
}

def test_fetch_meta_spend_returns_expected_columns():
    with patch("budget_check.loaders.meta_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = META_RESPONSE
        df = fetch_meta_spend("token", "123456", "2026-05-15")
    assert list(df.columns) == ["매체", "캠페인", "그룹", "api_소진"]

def test_fetch_meta_spend_sets_media_name():
    with patch("budget_check.loaders.meta_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = META_RESPONSE
        df = fetch_meta_spend("token", "123456", "2026-05-15")
    assert (df["매체"] == "Meta").all()

def test_fetch_meta_spend_converts_spend_to_int():
    with patch("budget_check.loaders.meta_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = META_RESPONSE
        df = fetch_meta_spend("token", "123456", "2026-05-15")
    assert df["api_소진"].dtype == "int64"
    assert df.iloc[0]["api_소진"] == 998

def test_fetch_meta_spend_empty_response():
    with patch("budget_check.loaders.meta_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = {"data": [], "paging": {}}
        df = fetch_meta_spend("token", "123456", "2026-05-15")
    assert df.empty
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd budget_check && python -m pytest ../tests/budget_check/test_meta_loader.py -v
```
Expected: `ImportError`

- [ ] **Step 3: meta_loader.py 구현**

`budget_check/loaders/meta_loader.py`:
```python
import requests
import pandas as pd


def fetch_meta_spend(access_token: str, ad_account_id: str, date: str) -> pd.DataFrame:
    """Meta Marketing API에서 캠페인+adset별 당일 소진액(KRW) 조회."""
    url = f"https://graph.facebook.com/v19.0/act_{ad_account_id}/insights"
    params = {
        "access_token": access_token,
        "time_range": f'{{"since":"{date}","until":"{date}"}}',
        "level": "adset",
        "fields": "campaign_name,adset_name,spend",
        "limit": 500,
    }

    rows = []
    while url:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        rows.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = {}  # next URL에 파라미터 포함됨

    if not rows:
        return pd.DataFrame(columns=["매체", "캠페인", "그룹", "api_소진"])

    df = pd.DataFrame(rows)
    df["매체"] = "Meta"
    df = df.rename(columns={"campaign_name": "캠페인", "adset_name": "그룹", "spend": "api_소진"})
    df["api_소진"] = pd.to_numeric(df["api_소진"]).astype(int)
    return df[["매체", "캠페인", "그룹", "api_소진"]]
```

> **주의:** Meta API의 spend는 광고 계정 통화 기준. KRW 계정이면 그대로 사용 가능. USD 계정이라면 환율 처리가 필요하며, 이 경우 RD 파일의 `비용 (KRW)` 컬럼과 직접 비교 가능.

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd budget_check && python -m pytest ../tests/budget_check/test_meta_loader.py -v
```
Expected: 4 tests PASSED

- [ ] **Step 5: 커밋**

```bash
git add budget_check/loaders/meta_loader.py tests/budget_check/test_meta_loader.py
git commit -m "feat: add Meta Marketing API spend loader"
```

---

## Task 5: 카카오 API 로더

**Files:**
- Create: `budget_check/loaders/kakao_loader.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/budget_check/test_kakao_loader.py`:
```python
from unittest.mock import patch, MagicMock
import pandas as pd
from budget_check.loaders.kakao_loader import fetch_kakao_spend

KAKAO_RESPONSE = {
    "data": [
        {
            "dimensions": {"campaignName": "캠페인B", "adGroupName": "그룹2"},
            "metrics": {"cost": 500000}
        },
        {
            "dimensions": {"campaignName": "캠페인D", "adGroupName": "그룹4"},
            "metrics": {"cost": 300000}
        }
    ]
}

def test_fetch_kakao_spend_returns_expected_columns():
    with patch("budget_check.loaders.kakao_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = KAKAO_RESPONSE
        df = fetch_kakao_spend("token", "acc123", "2026-05-15")
    assert list(df.columns) == ["매체", "캠페인", "그룹", "api_소진"]

def test_fetch_kakao_spend_sets_media_name():
    with patch("budget_check.loaders.kakao_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = KAKAO_RESPONSE
        df = fetch_kakao_spend("token", "acc123", "2026-05-15")
    assert (df["매체"] == "Kakao").all()

def test_fetch_kakao_spend_correct_values():
    with patch("budget_check.loaders.kakao_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = KAKAO_RESPONSE
        df = fetch_kakao_spend("token", "acc123", "2026-05-15")
    row = df[df["그룹"] == "그룹2"]
    assert row["api_소진"].iloc[0] == 500000

def test_fetch_kakao_spend_empty_response():
    with patch("budget_check.loaders.kakao_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = {"data": []}
        df = fetch_kakao_spend("token", "acc123", "2026-05-15")
    assert df.empty
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd budget_check && python -m pytest ../tests/budget_check/test_kakao_loader.py -v
```
Expected: `ImportError`

- [ ] **Step 3: kakao_loader.py 구현**

`budget_check/loaders/kakao_loader.py`:
```python
import requests
import pandas as pd


def fetch_kakao_spend(access_token: str, ad_account_id: str, date: str) -> pd.DataFrame:
    """카카오 모먼트 API에서 캠페인+그룹별 당일 소진액(KRW) 조회."""
    url = f"https://apis.moment.kakao.com/openapi/v4/adAccounts/{ad_account_id}/adGroups/stats"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    params = {
        "metricsGroups": "BASIC_PERFORMANCE",
        "startDate": date,
        "endDate": date,
        "dimensionGroups": "CAMPAIGN,AD_GROUP",
    }

    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("data", [])

    if not data:
        return pd.DataFrame(columns=["매체", "캠페인", "그룹", "api_소진"])

    rows = [
        {
            "매체": "Kakao",
            "캠페인": item["dimensions"]["campaignName"],
            "그룹": item["dimensions"]["adGroupName"],
            "api_소진": int(item["metrics"]["cost"]),
        }
        for item in data
    ]
    return pd.DataFrame(rows)[["매체", "캠페인", "그룹", "api_소진"]]
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd budget_check && python -m pytest ../tests/budget_check/test_kakao_loader.py -v
```
Expected: 4 tests PASSED

- [ ] **Step 5: 커밋**

```bash
git add budget_check/loaders/kakao_loader.py tests/budget_check/test_kakao_loader.py
git commit -m "feat: add Kakao Moment API spend loader"
```

---

## Task 6: RD vs 매체 검증 로직

**Files:**
- Create: `budget_check/logic/validator.py`
- Create: `tests/budget_check/test_validator.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/budget_check/test_validator.py`:
```python
import pandas as pd
from budget_check.logic.validator import validate_rd_vs_api

RD = pd.DataFrame([
    {"매체": "Meta", "캠페인": "캠페인A", "그룹": "그룹1", "rd_소진": 1000000},
    {"매체": "Kakao", "캠페인": "캠페인B", "그룹": "그룹2", "rd_소진": 500000},
])

API = pd.DataFrame([
    {"매체": "Meta", "캠페인": "캠페인A", "그룹": "그룹1", "api_소진": 998000},
    {"매체": "Kakao", "캠페인": "캠페인B", "그룹": "그룹2", "api_소진": 500000},
])

def test_validate_returns_expected_columns():
    df = validate_rd_vs_api(RD, API)
    assert set(df.columns) >= {"매체", "캠페인", "그룹", "rd_소진", "api_소진", "차이", "상태"}

def test_validate_exact_match_is_ok():
    df = validate_rd_vs_api(RD, API)
    row = df[(df["매체"] == "Kakao") & (df["그룹"] == "그룹2")]
    assert row["상태"].iloc[0] == "✅ 일치"

def test_validate_within_1pct_is_warning():
    df = validate_rd_vs_api(RD, API)
    row = df[(df["매체"] == "Meta") & (df["그룹"] == "그룹1")]
    # 차이 = -2000, 비율 = 0.2% → 허용 오차
    assert row["상태"].iloc[0] == "🟢 허용 오차"

def test_validate_over_1pct_is_error():
    rd = pd.DataFrame([{"매체": "Meta", "캠페인": "캠페인A", "그룹": "그룹1", "rd_소진": 1000000}])
    api = pd.DataFrame([{"매체": "Meta", "캠페인": "캠페인A", "그룹": "그룹1", "api_소진": 980000}])
    df = validate_rd_vs_api(rd, api)
    assert df.iloc[0]["상태"] == "🔴 불일치"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd budget_check && python -m pytest ../tests/budget_check/test_validator.py -v
```
Expected: `ImportError`

- [ ] **Step 3: validator.py 구현**

`budget_check/logic/validator.py`:
```python
import pandas as pd


def validate_rd_vs_api(rd: pd.DataFrame, api: pd.DataFrame) -> pd.DataFrame:
    """RD 소진 vs 매체 API 소진 비교. 조인 키: 매체+캠페인+그룹."""
    joined = pd.merge(rd, api, on=["매체", "캠페인", "그룹"], how="outer").fillna(0)
    joined["차이"] = joined["rd_소진"] - joined["api_소진"]

    def _status(row) -> str:
        if row["rd_소진"] == 0 and row["api_소진"] == 0:
            return "✅ 일치"
        base = max(row["rd_소진"], row["api_소진"])
        if base == 0:
            return "✅ 일치"
        rate = abs(row["차이"]) / base
        if rate == 0:
            return "✅ 일치"
        if rate <= 0.01:
            return "🟢 허용 오차"
        return "🔴 불일치"

    joined["상태"] = joined.apply(_status, axis=1)
    return joined[["매체", "캠페인", "그룹", "rd_소진", "api_소진", "차이", "상태"]]
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd budget_check && python -m pytest ../tests/budget_check/test_validator.py -v
```
Expected: 4 tests PASSED

- [ ] **Step 5: 커밋**

```bash
git add budget_check/logic/validator.py tests/budget_check/test_validator.py
git commit -m "feat: add RD vs API spend validator"
```

---

## Task 7: 예산 플랜 대비 과소진/미소진 로직

**Files:**
- Create: `budget_check/logic/budget_checker.py`
- Create: `tests/budget_check/test_budget_checker.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/budget_check/test_budget_checker.py`:
```python
import pandas as pd
from budget_check.logic.budget_checker import check_budget

API = pd.DataFrame([
    {"매체": "Meta", "캠페인": "캠페인A", "그룹": "그룹1", "api_소진": 998000},
    {"매체": "Kakao", "캠페인": "캠페인B", "그룹": "그룹2", "api_소진": 500000},
])

PLAN = pd.DataFrame([
    {"매체": "Meta", "캠페인": "캠페인A", "그룹": "그룹1", "일예산": 1200000},
    {"매체": "Kakao", "캠페인": "캠페인B", "그룹": "그룹2", "일예산": 400000},
])

def test_check_budget_returns_expected_columns():
    df = check_budget(API, PLAN)
    assert set(df.columns) >= {"매체", "캠페인", "그룹", "일예산", "소진", "차이", "상태"}

def test_check_budget_underspend_over_10pct():
    df = check_budget(API, PLAN)
    row = df[(df["매체"] == "Meta") & (df["그룹"] == "그룹1")]
    # 차이 = 998000 - 1200000 = -202000, 비율 = -16.8% → 미소진
    assert row["상태"].iloc[0] == "🔴 미소진"

def test_check_budget_overspend():
    df = check_budget(API, PLAN)
    row = df[(df["매체"] == "Kakao") & (df["그룹"] == "그룹2")]
    # 차이 = 500000 - 400000 = +100000 → 과소진
    assert row["상태"].iloc[0] == "🟡 과소진"

def test_check_budget_within_tolerance_is_normal():
    api = pd.DataFrame([{"매체": "Meta", "캠페인": "캠페인A", "그룹": "그룹1", "api_소진": 1150000}])
    plan = pd.DataFrame([{"매체": "Meta", "캠페인": "캠페인A", "그룹": "그룹1", "일예산": 1200000}])
    df = check_budget(api, plan)
    # 차이 = -50000, 비율 = -4.2% → 정상 (-10% 이상)
    assert df.iloc[0]["상태"] == "🟢 정상"

def test_check_budget_totals():
    df = check_budget(API, PLAN)
    assert df["일예산"].sum() == 1600000
    assert df["소진"].sum() == 1498000
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd budget_check && python -m pytest ../tests/budget_check/test_budget_checker.py -v
```
Expected: `ImportError`

- [ ] **Step 3: budget_checker.py 구현**

`budget_check/logic/budget_checker.py`:
```python
import pandas as pd


def check_budget(api: pd.DataFrame, plan: pd.DataFrame) -> pd.DataFrame:
    """API 소진 vs 예산 플랜 비교. 조인 키: 매체+캠페인+그룹."""
    joined = pd.merge(
        plan, api, on=["매체", "캠페인", "그룹"], how="left"
    ).fillna(0)
    joined = joined.rename(columns={"api_소진": "소진"})
    joined["차이"] = joined["소진"] - joined["일예산"]

    def _status(row) -> str:
        if row["일예산"] == 0:
            return "🟢 정상"
        rate = row["차이"] / row["일예산"]
        if rate > 0:
            return "🟡 과소진"
        if rate < -0.10:
            return "🔴 미소진"
        return "🟢 정상"

    joined["상태"] = joined.apply(_status, axis=1)
    return joined[["매체", "캠페인", "그룹", "일예산", "소진", "차이", "상태"]]
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd budget_check && python -m pytest ../tests/budget_check/test_budget_checker.py -v
```
Expected: 5 tests PASSED

- [ ] **Step 5: 커밋**

```bash
git add budget_check/logic/budget_checker.py tests/budget_check/test_budget_checker.py
git commit -m "feat: add budget plan vs spend checker with over/under logic"
```

---

## Task 8: Slack 발송

**Files:**
- Create: `budget_check/slack_sender.py`
- Create: `tests/budget_check/test_slack_sender.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/budget_check/test_slack_sender.py`:
```python
from unittest.mock import patch, MagicMock
import pandas as pd
from budget_check.slack_sender import format_message, send_to_slack

VALIDATION_DF = pd.DataFrame([
    {"매체": "Meta", "캠페인": "캠페인A", "그룹": "그룹1", "rd_소진": 1000000, "api_소진": 998000, "차이": -2000, "상태": "🟢 허용 오차"},
    {"매체": "Kakao", "캠페인": "캠페인B", "그룹": "그룹2", "rd_소진": 500000, "api_소진": 500000, "차이": 0, "상태": "✅ 일치"},
])

BUDGET_DF = pd.DataFrame([
    {"매체": "Meta", "캠페인": "캠페인A", "그룹": "그룹1", "일예산": 1200000, "소진": 998000, "차이": -202000, "상태": "🔴 미소진"},
    {"매체": "Kakao", "캠페인": "캠페인B", "그룹": "그룹2", "일예산": 400000, "소진": 500000, "차이": 100000, "상태": "🟡 과소진"},
])

def test_format_message_contains_date():
    msg = format_message("2026-05-15", VALIDATION_DF, BUDGET_DF)
    assert "2026-05-15" in msg

def test_format_message_contains_overspend():
    msg = format_message("2026-05-15", VALIDATION_DF, BUDGET_DF)
    assert "과소진" in msg
    assert "캠페인B" in msg

def test_format_message_contains_underspend():
    msg = format_message("2026-05-15", VALIDATION_DF, BUDGET_DF)
    assert "미소진" in msg
    assert "캠페인A" in msg

def test_format_message_contains_total():
    msg = format_message("2026-05-15", VALIDATION_DF, BUDGET_DF)
    assert "1,600,000" in msg  # 일예산 합계

def test_send_to_slack_posts_to_webhook():
    with patch("budget_check.slack_sender.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        send_to_slack("https://hooks.slack.com/test", "테스트 메시지")
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs[1]["json"]["text"] == "테스트 메시지"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd budget_check && python -m pytest ../tests/budget_check/test_slack_sender.py -v
```
Expected: `ImportError`

- [ ] **Step 3: slack_sender.py 구현**

`budget_check/slack_sender.py`:
```python
import requests
import pandas as pd


def format_message(date: str, validation_df: pd.DataFrame, budget_df: pd.DataFrame) -> str:
    lines = [f"📊 *예산 점검 | {date}*\n"]

    # RD vs API 검증 섹션
    lines.append("*✅ RD vs 매체 검증*")
    for _, row in validation_df.iterrows():
        if row["상태"] == "✅ 일치":
            lines.append(f"• {row['매체']} / {row['캠페인']} / {row['그룹']}: 일치 ✓")
        else:
            lines.append(
                f"• {row['매체']} / {row['캠페인']} / {row['그룹']}: "
                f"RD {row['rd_소진']:,.0f} vs API {row['api_소진']:,.0f} "
                f"(△{row['차이']:+,.0f}) {row['상태']}"
            )

    # 과소진 섹션
    over = budget_df[budget_df["상태"] == "🟡 과소진"]
    if not over.empty:
        lines.append("\n*🟡 과소진*")
        for _, row in over.iterrows():
            lines.append(
                f"• {row['매체']} / {row['캠페인']} / {row['그룹']}: "
                f"예산 {row['일예산']:,.0f} → 소진 {row['소진']:,.0f} ({row['차이']:+,.0f})"
            )

    # 미소진 섹션
    under = budget_df[budget_df["상태"] == "🔴 미소진"]
    if not under.empty:
        lines.append("\n*🔴 미소진*")
        for _, row in under.iterrows():
            lines.append(
                f"• {row['매체']} / {row['캠페인']} / {row['그룹']}: "
                f"예산 {row['일예산']:,.0f} → 소진 {row['소진']:,.0f} ({row['차이']:+,.0f})"
            )

    # 전체 합계
    total_plan = budget_df["일예산"].sum()
    total_spend = budget_df["소진"].sum()
    total_diff = total_spend - total_plan
    lines.append(
        f"\n*전체: 예산 {total_plan:,.0f} / 소진 {total_spend:,.0f} / 차이 {total_diff:+,.0f}*"
    )

    return "\n".join(lines)


def send_to_slack(webhook_url: str, message: str) -> None:
    resp = requests.post(webhook_url, json={"text": message}, timeout=10)
    resp.raise_for_status()
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd budget_check && python -m pytest ../tests/budget_check/test_slack_sender.py -v
```
Expected: 5 tests PASSED

- [ ] **Step 5: 전체 테스트 통과 확인**

```bash
cd budget_check && python -m pytest ../tests/budget_check/ -v
```
Expected: 전체 PASSED

- [ ] **Step 6: 커밋**

```bash
git add budget_check/slack_sender.py tests/budget_check/test_slack_sender.py
git commit -m "feat: add Slack message formatter and webhook sender"
```

---

## Task 9: Streamlit 앱 UI 완성

**Files:**
- Modify: `budget_check/app.py`

- [ ] **Step 1: app.py 전체 구현**

`budget_check/app.py`:
```python
import streamlit as st
import pandas as pd
from loaders.rd_loader import load_rd
from loaders.meta_loader import fetch_meta_spend
from loaders.kakao_loader import fetch_kakao_spend
from loaders.sheets_loader import load_budget_plan
from logic.validator import validate_rd_vs_api
from logic.budget_checker import check_budget
from slack_sender import format_message, send_to_slack

st.set_page_config(page_title="예산 점검", page_icon="📊", layout="wide")
st.title("📊 예산 점검")

# ── 입력 영역 ──────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 2])
with col1:
    selected_date = st.date_input("날짜").strftime("%Y-%m-%d")
    rd_file = st.file_uploader("RD 파일 업로드 (엑스퍼트 CSV)", type=["csv"])

with col2:
    sheets_url = st.text_input(
        "예산 플랜 Google Sheets URL",
        placeholder="https://docs.google.com/spreadsheets/d/...",
    )

run = st.button("🔍 조회", type="primary", disabled=(rd_file is None or not sheets_url))

if not run:
    st.stop()

# ── 데이터 수집 ────────────────────────────────────────────────────────────────
meta_token = st.secrets["META_ACCESS_TOKEN"]
meta_account = st.secrets["META_AD_ACCOUNT_ID"]
kakao_token = st.secrets["KAKAO_ACCESS_TOKEN"]
kakao_account = st.secrets["KAKAO_AD_ACCOUNT_ID"]

with st.spinner("데이터 수집 중..."):
    rd_df = load_rd(rd_file, date=selected_date)

    try:
        meta_df = fetch_meta_spend(meta_token, meta_account, selected_date)
    except Exception as e:
        st.warning(f"Meta API 오류: {e}")
        meta_df = pd.DataFrame(columns=["매체", "캠페인", "그룹", "api_소진"])

    try:
        kakao_df = fetch_kakao_spend(kakao_token, kakao_account, selected_date)
    except Exception as e:
        st.warning(f"카카오 API 오류: {e}")
        kakao_df = pd.DataFrame(columns=["매체", "캠페인", "그룹", "api_소진"])

    try:
        plan_df = load_budget_plan(sheets_url, date=selected_date)
    except Exception as e:
        st.error(f"예산 시트 로드 실패: {e}")
        st.stop()

api_df = pd.concat([meta_df, kakao_df], ignore_index=True)

# ── 비교 계산 ──────────────────────────────────────────────────────────────────
validation_df = validate_rd_vs_api(rd_df, api_df)
budget_df = check_budget(api_df, plan_df)

# ── 테이블 표시 ────────────────────────────────────────────────────────────────
st.subheader("① RD vs 매체 API 검증")
st.dataframe(
    validation_df.style.applymap(
        lambda v: "color: red" if v == "🔴 불일치" else "",
        subset=["상태"],
    ),
    use_container_width=True,
    hide_index=True,
)

st.subheader("② 예산 플랜 대비")

def _color_status(val):
    if val == "🔴 미소진":
        return "background-color: #ffd7d7"
    if val == "🟡 과소진":
        return "background-color: #fff3cd"
    return ""

st.dataframe(
    budget_df.style.applymap(_color_status, subset=["상태"]),
    use_container_width=True,
    hide_index=True,
)

total_plan = budget_df["일예산"].sum()
total_spend = budget_df["소진"].sum()
total_diff = total_spend - total_plan
col_a, col_b, col_c = st.columns(3)
col_a.metric("전체 예산", f"{total_plan:,.0f}원")
col_b.metric("전체 소진", f"{total_spend:,.0f}원")
col_c.metric("차이", f"{total_diff:+,.0f}원", delta_color="inverse")

# ── 슬랙 발송 ──────────────────────────────────────────────────────────────────
st.divider()
if st.button("📤 슬랙으로 발송"):
    message = format_message(selected_date, validation_df, budget_df)
    try:
        send_to_slack(st.secrets["SLACK_WEBHOOK_URL"], message)
        st.success("슬랙 발송 완료!")
    except Exception as e:
        st.error(f"슬랙 발송 실패: {e}")
```

- [ ] **Step 2: 로컬 실행 확인**

```bash
cd budget_check
streamlit run app.py
```
Expected: 브라우저에서 날짜 선택, 파일 업로드, URL 입력, 조회 버튼 동작 확인. secrets.toml에 더미 값이라 API 호출은 실패하지만 UI 렌더링은 정상.

- [ ] **Step 3: 커밋**

```bash
git add budget_check/app.py
git commit -m "feat: complete Streamlit budget check UI with Slack send button"
```

---

## Task 10: 배포

**Files:**
- Create: `.gitignore` (업데이트)

- [ ] **Step 1: GitHub private repo 생성 및 push**

```bash
gh repo create budget-check --private --source=. --push
```

또는 GitHub 웹에서 `budget-check` repo 생성 후:
```bash
git remote add origin https://github.com/<YOUR_ORG>/budget-check.git
git push -u origin master
```

- [ ] **Step 2: Streamlit Community Cloud 배포**

1. https://share.streamlit.io 접속
2. "New app" 클릭
3. Repository: `<YOUR_ORG>/budget-check`
4. Branch: `master`
5. Main file path: `budget_check/app.py`
6. "Advanced settings" → Secrets 탭에 아래 내용 입력:

```toml
META_ACCESS_TOKEN = "실제 토큰값"
META_AD_ACCOUNT_ID = "실제 계정 ID"
KAKAO_ACCESS_TOKEN = "실제 토큰값"
KAKAO_AD_ACCOUNT_ID = "실제 계정 ID"
SLACK_WEBHOOK_URL = "실제 웹훅 URL"
```

7. "Deploy!" 클릭

- [ ] **Step 3: 배포 후 동작 확인**

배포된 URL에서:
1. 날짜 선택
2. RD CSV 업로드 (드롭박스에서 최신 파일 선택)
3. Google Sheets URL 입력 (`공개 링크` 설정 확인)
4. 조회 클릭 → 두 테이블 정상 표시 확인
5. 슬랙 발송 버튼 클릭 → 슬랙 채널에 메시지 수신 확인

- [ ] **Step 4: 팀 URL 공유**

배포된 URL을 팀 슬랙 채널에 공유. 접속에 Streamlit 계정 로그인이 필요한 경우 "Public" 공개 설정으로 변경.
