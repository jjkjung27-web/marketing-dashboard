import re
import io
import requests
import pandas as pd


def parse_sheets_url(url: str) -> tuple[str, str, str | None]:
    """Google Sheets URL에서 spreadsheet ID, gid, range 추출.

    range는 URL fragment(#) 또는 query string에서 파싱.
    예: ...#gid=123&range=B210:V242
    """
    match = re.search(r"/spreadsheets/d/([^/]+)", url)
    if not match:
        raise ValueError(f"유효한 Google Sheets URL이 아닙니다: {url}")
    sheet_id = match.group(1)

    gid_match = re.search(r"gid=(\d+)", url)
    gid = gid_match.group(1) if gid_match else "0"

    # A1 표기법 범위 파싱 (예: B210:V242 또는 210:243)
    range_match = re.search(r"range=([A-Z0-9:]+)", url)
    range_str = range_match.group(1) if range_match else None

    return sheet_id, gid, range_str


def _parse_wide_format(df_raw: pd.DataFrame, date: str) -> pd.DataFrame:
    """WIDE 포맷(2행 헤더) → 지정 날짜의 LONG 포맷으로 변환.

    Row 0: 캠페인명 (병합 셀로 인해 첫 컬럼에만 값, 나머지 빈 칸)
    Row 1: DATE | TOTAL | 매체_레이블...
    Row 2+: 날짜별 예산 데이터
    """
    campaign_row = df_raw.iloc[0].tolist()
    header_row = df_raw.iloc[1].tolist()
    data = df_raw.iloc[2:].reset_index(drop=True)

    # DATE 컬럼 인덱스 찾기
    date_col_idx = next(
        (i for i, v in enumerate(header_row) if str(v).strip() == "DATE"),
        None,
    )
    if date_col_idx is None:
        raise KeyError(f"DATE 컬럼을 찾을 수 없습니다. 헤더: {header_row}")

    # 캠페인명 forward-fill (병합 셀 복원)
    campaigns = []
    current = ""
    for val in campaign_row:
        v = str(val).strip().split("\n")[0]
        # FALSE/TRUE 등 제어값, 빈 셀 제외
        if v and v.upper() not in ("FALSE", "TRUE", "NAN", ""):
            current = v
        campaigns.append(current)

    # 컬럼 매핑: 인덱스 → (매체, 캠페인)
    col_mapping = []
    for i, raw_label in enumerate(header_row):
        if i == date_col_idx:
            continue
        label = str(raw_label).strip()
        if "메타" in label:
            media = "Meta"
        elif "카카오" in label:
            media = "Kakao"
        else:
            continue  # TOTAL 등 스킵

        campaign = campaigns[i]
        if not campaign:
            continue
        col_mapping.append((i, media, campaign))

    def _parse_budget(val) -> int:
        s = str(val).replace("₩", "").replace(",", "").strip()
        try:
            return int(float(s))
        except (ValueError, TypeError):
            return 0

    long_rows = []
    for _, row in data.iterrows():
        raw_date = str(row.iloc[date_col_idx]).strip().split(" ")[0]
        try:
            pd.to_datetime(raw_date)
        except Exception:
            continue  # TOTAL 행 등 스킵
        if raw_date != date:
            continue

        for col_idx, media, campaign in col_mapping:
            budget = _parse_budget(row.iloc[col_idx] if col_idx < len(row) else "")
            if budget > 0:
                long_rows.append({"매체": media, "캠페인": campaign, "그룹": "", "일예산": budget})

    if not long_rows:
        return pd.DataFrame(columns=["매체", "캠페인", "그룹", "일예산"])
    return pd.DataFrame(long_rows)[["매체", "캠페인", "그룹", "일예산"]]


def _parse_long_format(df: pd.DataFrame, date: str) -> pd.DataFrame:
    """LONG 포맷(DATE | 파트 | 매체 | 캠페인 | 그룹 | 일예산) 처리."""
    date_col = next(
        (c for c in df.columns if str(c).strip() in ("DATE", "날짜", "date")),
        None,
    )
    if date_col is None:
        raise KeyError(f"날짜 컬럼을 찾을 수 없습니다. 컬럼: {list(df.columns)}")

    df[date_col] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d")
    df = df[df[date_col] == date]

    if df.empty:
        return pd.DataFrame(columns=["매체", "캠페인", "그룹", "일예산"])

    if "그룹" not in df.columns:
        df = df.copy()
        df["그룹"] = ""

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


def load_budget_plan(url: str, date: str) -> pd.DataFrame:
    """Google Sheets URL에서 예산 플랜을 읽어 지정 날짜 행만 반환.

    WIDE 포맷(기존 풋웨어 시트, range 파라미터 필요)과
    LONG 포맷(DATE|파트|매체|캠페인|그룹|일예산) 모두 지원.
    """
    sheet_id, gid, range_str = parse_sheets_url(url)
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    if range_str:
        export_url += f"&range={range_str}"

    resp = requests.get(export_url, timeout=10)
    resp.encoding = "utf-8"
    resp.raise_for_status()

    # 헤더 없이 읽어 포맷 감지
    df_raw = pd.read_csv(io.StringIO(resp.text), header=None, dtype=str)

    # 첫 행에 DATE가 있으면 LONG, 두 번째 행에 있으면 WIDE
    first_row_vals = [str(v).strip() for v in df_raw.iloc[0].tolist()]
    second_row_vals = [str(v).strip() for v in df_raw.iloc[1].tolist()] if len(df_raw) > 1 else []

    if "DATE" in first_row_vals or "날짜" in first_row_vals:
        df_raw.columns = df_raw.iloc[0]
        df = df_raw[1:].reset_index(drop=True)
        return _parse_long_format(df, date)
    elif "DATE" in second_row_vals:
        return _parse_wide_format(df_raw, date)
    else:
        raise ValueError(
            f"지원하지 않는 시트 포맷입니다. "
            f"1행: {first_row_vals[:5]}, 2행: {second_row_vals[:5]}"
        )
