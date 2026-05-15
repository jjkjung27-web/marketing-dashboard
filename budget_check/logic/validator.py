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
