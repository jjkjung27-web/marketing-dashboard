import sys
from pathlib import Path
import pandas as pd

from .config import SPREADSHEET_ID, INDEX_GID, INDEX_SHEET_NAME, CREDS_PATH, OUTPUT_DIR
from .parser import parse_campaign_name, PARSED_COLS
from .sheets_client import load_index, append_missing_rows, COMPOSITE_KEYS, OVERRIDE_COLS


def add_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    dates = pd.to_datetime(df["날짜"])
    df["weeknum"] = dates.dt.isocalendar().week.astype(int)
    df["연월"] = dates.dt.strftime("%Y-%m")
    return df


def add_parsed_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    parsed = df["캠페인 이름"].apply(parse_campaign_name)
    for col in PARSED_COLS:
        df[col] = parsed.apply(lambda d, c=col: d.get(c, ""))
    return df


def apply_overrides(df: pd.DataFrame, index_df: pd.DataFrame) -> pd.DataFrame:
    if index_df.empty:
        return df
    override_cols_present = [c for c in OVERRIDE_COLS if c in index_df.columns]
    index_subset = index_df[COMPOSITE_KEYS + override_cols_present].copy()
    merged = df.merge(index_subset, on=COMPOSITE_KEYS, how="left", suffixes=("", "_ov"))
    for col in override_cols_present:
        ov = f"{col}_ov"
        if ov in merged.columns:
            mask = merged[ov].notna() & (merged[ov] != "")
            merged[col] = merged[ov].where(mask, merged[col])
            merged.drop(columns=[ov], inplace=True)
    return merged


def get_parse_failures(df: pd.DataFrame) -> list[dict]:
    failed = df[df["brand"] == ""]
    return failed[COMPOSITE_KEYS].drop_duplicates().to_dict("records")


def enrich(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig")
    df = add_date_columns(df)
    df = add_parsed_columns(df)

    index_df = load_index(SPREADSHEET_ID, INDEX_GID)
    df = apply_overrides(df, index_df)

    failures = get_parse_failures(df)
    if failures:
        append_missing_rows(SPREADSHEET_ID, INDEX_SHEET_NAME, CREDS_PATH, failures)
        print(f"[INFO] {len(failures)}건 파싱 실패 → Sheets 인덱스에 추가됨")

    new_cols = ["weeknum", "연월"] + PARSED_COLS
    original_cols = [c for c in df.columns if c not in new_cols]
    return df[new_cols + original_cols]


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m tools.enrich_daily.enrich <csv_path>")
        sys.exit(1)

    csv_path = sys.argv[1]
    output_path = Path(OUTPUT_DIR) / f"enriched_{Path(csv_path).stem}.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = enrich(csv_path)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"[DONE] {output_path} ({len(df):,}행)")


if __name__ == "__main__":
    main()
