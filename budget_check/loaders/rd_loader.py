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

    # 소진 컬럼명: 파일 버전마다 다름
    for candidate in ["지출 금액 (KRW)", "비용 (KRW)", "광고비_Fee포함", "비용"]:
        if candidate in df.columns:
            spend_col = candidate
            break
    else:
        raise KeyError(f"소진 금액 컬럼을 찾을 수 없습니다. 컬럼 목록: {list(df.columns)}")

    # 그룹 컬럼명: '광고 세트 이름' 또는 '광고 그룹 이름'
    for candidate in ["광고 세트 이름", "광고 그룹 이름"]:
        if candidate in df.columns:
            group_col = candidate
            break
    else:
        raise KeyError(f"그룹 컬럼을 찾을 수 없습니다. 컬럼 목록: {list(df.columns)}")

    result = (
        df.groupby(["매체", "캠페인 이름", group_col])[spend_col]
        .sum()
        .reset_index()
        .rename(columns={"캠페인 이름": "캠페인", group_col: "그룹", spend_col: "rd_소진"})
    )
    return result[["매체", "캠페인", "그룹", "rd_소진"]]
