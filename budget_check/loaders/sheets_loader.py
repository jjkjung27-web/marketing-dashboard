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
    """Google Sheets URL에서 예산 플랜을 읽어 지정 날짜 행만 반환.

    지원 포맷: DATE | 파트 | 매체 | 캠페인 | 그룹 | 일예산 (Long format)
    """
    sheet_id, gid = parse_sheets_url(url)
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

    resp = requests.get(export_url, timeout=10)
    resp.encoding = "utf-8"
    resp.raise_for_status()

    df = pd.read_csv(io.StringIO(resp.text))

    # DATE 컬럼 처리 (Long format)
    date_col = None
    for candidate in ["DATE", "날짜", "date"]:
        if candidate in df.columns:
            date_col = candidate
            break
    if date_col is None:
        raise KeyError(f"날짜 컬럼(DATE/날짜)을 찾을 수 없습니다. 컬럼: {list(df.columns)}")

    df[date_col] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d")
    df = df[df[date_col] == date]

    if df.empty:
        return pd.DataFrame(columns=["매체", "캠페인", "그룹", "일예산"])

    # 그룹 컬럼 (없을 수도 있음)
    if "그룹" not in df.columns:
        df["그룹"] = ""

    # 일예산 숫자 변환 (₩, 쉼표 제거)
    df["일예산"] = (
        df["일예산"].astype(str)
        .str.replace("₩", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
        .replace("", "0")
        .astype(float)
        .astype(int)
    )

    return df[["매체", "캠페인", "그룹", "일예산"]].reset_index(drop=True)
