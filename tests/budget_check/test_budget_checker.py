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
