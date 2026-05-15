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
