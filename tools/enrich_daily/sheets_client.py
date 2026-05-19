import io
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

COMPOSITE_KEYS = ["캠페인 이름", "광고 세트 이름", "광고 이름"]
OVERRIDE_COLS = ["brand", "판매채널", "광고목표", "소재유형", "타겟구분", "기획전명"]
_ALL_COLS = COMPOSITE_KEYS + OVERRIDE_COLS + ["비고"]
_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def load_index(spreadsheet_id: str, gid: str) -> pd.DataFrame:
    """Google Sheets ad_index를 DataFrame으로 읽어옴 (CSV export 방식)."""
    url = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        f"/export?format=csv&gid={gid}"
    )
    resp = requests.get(url, timeout=10)
    resp.encoding = "utf-8"
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text), dtype=str).fillna("")
    for col in _ALL_COLS:
        if col not in df.columns:
            df[col] = ""
    return df
