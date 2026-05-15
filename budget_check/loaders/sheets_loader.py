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
