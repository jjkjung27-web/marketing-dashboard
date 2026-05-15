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
