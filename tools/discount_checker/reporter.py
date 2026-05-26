import csv
import json
import urllib.request
from datetime import datetime
from pathlib import Path

from tools.discount_checker.comparator import CompareResult


def write_csv(results: list[CompareResult], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = output_dir / f"discount_check_{date_str}.csv"

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["검수일시", "광고명", "소재_할인율", "대표_UID", "실제_최대_할인율", "오차", "상태"]
        )
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for r in results:
            writer.writerow([
                now,
                r.ad_name,
                r.creative_discount if r.creative_discount is not None else "추출불가",
                r.representative_uid or "",
                r.actual_max_discount if r.actual_max_discount is not None else "",
                r.diff if r.diff is not None else "",
                r.status,
            ])
    return path


def send_slack(results: list[CompareResult], webhook_url: str) -> None:
    if not webhook_url:
        return
    mismatches = [r for r in results if r.status == "불일치"]
    for r in mismatches:
        text = (
            f"⚠️ [할인율 불일치] {r.ad_name}\n"
            f"소재: {r.creative_discount}% → 실제 최대: {r.actual_max_discount}% (오차 {r.diff:+d}%)\n"
            f"UID: {r.representative_uid}"
        )
        payload = json.dumps({"text": text}).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            print(f"[경고] Slack 알림 전송 실패: {e}")
