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
