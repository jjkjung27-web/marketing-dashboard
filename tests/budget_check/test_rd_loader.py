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
    assert len(df) == 2  # 매체+캠페인+그룹 기준 집계 후 2행

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
