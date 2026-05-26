import re
from urllib.parse import parse_qs

from google.oauth2 import service_account
from googleapiclient.discovery import build

from tools.discount_checker.comparator import AdRow

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def parse_sheets_url(url: str) -> tuple[str, str | None, str | None]:
    """Returns (spreadsheet_id, gid, range_str)."""
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not match:
        raise ValueError(f"Invalid Google Sheets URL: {url}")
    spreadsheet_id = match.group(1)

    fragment = url.split("#")[-1] if "#" in url else ""
    frag_params = parse_qs(fragment)
    gid = frag_params.get("gid", [None])[0]
    range_str = frag_params.get("range", [None])[0]
    return spreadsheet_id, gid, range_str


def _parse_uid_list(raw: str) -> list[str]:
    """'4944027, 3825639(메모)' → ['4944027', '3825639']"""
    parts = raw.split(",")
    uids = []
    for p in parts:
        p = p.strip()
        p = re.sub(r"\(.*?\)", "", p).strip()
        if p:
            uids.append(p)
    return uids


def _find_header_indices(
    rows: list[list[str]], ad_col: str, uid_col: str
) -> tuple[int, int, int]:
    """Returns (ad_col_index, uid_col_index, header_row_index)."""
    for row_idx, row in enumerate(rows):
        if ad_col in row:
            if uid_col not in row:
                raise ValueError(
                    f"'{uid_col}' 컬럼을 헤더에서 찾을 수 없습니다. 헤더: {row}"
                )
            return row.index(ad_col), row.index(uid_col), row_idx
    raise ValueError(
        f"'{ad_col}' 컬럼을 헤더에서 찾을 수 없습니다."
    )


def _gid_to_sheet_name(service, spreadsheet_id: str, gid: str) -> str:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in meta["sheets"]:
        if str(sheet["properties"]["sheetId"]) == gid:
            return sheet["properties"]["title"]
    raise ValueError(f"gid={gid} 에 해당하는 시트를 찾을 수 없습니다.")


def read_ad_rows(
    url: str,
    service_account_json: str,
    ad_col: str = "광고명",
    uid_col: str = "UID",
) -> list[AdRow]:
    creds = service_account.Credentials.from_service_account_file(
        service_account_json, scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=creds)

    spreadsheet_id, gid, range_str = parse_sheets_url(url)
    sheet_name = _gid_to_sheet_name(service, spreadsheet_id, gid) if gid else None

    if range_str and sheet_name:
        full_range = f"'{sheet_name}'!{range_str}"
    elif sheet_name:
        full_range = f"'{sheet_name}'"
    else:
        full_range = range_str

    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=full_range)
        .execute()
    )
    rows = result.get("values", [])
    if not rows:
        return []

    ad_idx, uid_idx, header_row_idx = _find_header_indices(rows, ad_col, uid_col)

    ad_rows = []
    for row in rows[header_row_idx + 1:]:
        ad_name = row[ad_idx].strip() if ad_idx < len(row) else ""
        uid_raw = row[uid_idx].strip() if uid_idx < len(row) else ""
        if not ad_name or not uid_raw:
            continue
        ad_rows.append(AdRow(ad_name=ad_name, uids=_parse_uid_list(uid_raw)))

    return ad_rows
