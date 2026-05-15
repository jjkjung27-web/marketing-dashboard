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
