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


def append_missing_rows(
    spreadsheet_id: str,
    sheet_name: str,
    creds_path: str,
    missing_rows: list[dict],
) -> None:
    """파싱 실패 행의 3개 키를 Sheets 인덱스에 추가 (기존 키 중복 제외)."""
    if not missing_rows:
        return

    creds = Credentials.from_service_account_file(creds_path, scopes=_SCOPES)
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(spreadsheet_id).worksheet(sheet_name)

    all_vals = ws.get_all_values()
    if not all_vals:
        return
    header = all_vals[0]

    key_indices = [header.index(k) for k in COMPOSITE_KEYS if k in header]
    existing_keys: set[tuple] = set(
        tuple(row[i] for i in key_indices)
        for row in all_vals[1:]
        if len(row) > max(key_indices, default=-1)
    )

    to_append = []
    for row_dict in missing_rows:
        key = tuple(row_dict.get(k, "") for k in COMPOSITE_KEYS)
        if key not in existing_keys:
            new_row = [row_dict.get(col, "") for col in header]
            to_append.append(new_row)
            existing_keys.add(key)

    if to_append:
        ws.append_rows(to_append, value_input_option="USER_ENTERED")
