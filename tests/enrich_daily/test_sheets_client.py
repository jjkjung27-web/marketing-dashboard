from unittest.mock import patch, MagicMock, call
import pandas as pd
from tools.enrich_daily.sheets_client import load_index, COMPOSITE_KEYS, OVERRIDE_COLS, append_missing_rows

INDEX_CSV = """캠페인 이름,광고 세트 이름,광고 이름,brand,판매채널,광고목표,소재유형,타겟구분,기획전명,비고
캠페인A,세트A,광고A,잔스포츠,무신사,전환,컬렉션,잠재고객,하프파인트 콜라보,수동입력
캠페인B,세트B,광고B,,,,,,,
"""

MINIMAL_CSV = """캠페인 이름,광고 세트 이름,광고 이름
캠페인C,세트C,광고C
"""


def test_load_index_returns_dataframe():
    with patch("tools.enrich_daily.sheets_client.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=INDEX_CSV)
        mock_get.return_value.raise_for_status = MagicMock()
        df = load_index("FAKE_ID", "0")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2


def test_load_index_fills_missing_override_cols():
    with patch("tools.enrich_daily.sheets_client.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=MINIMAL_CSV)
        mock_get.return_value.raise_for_status = MagicMock()
        df = load_index("FAKE_ID", "0")
    for col in OVERRIDE_COLS:
        assert col in df.columns
        assert df[col].iloc[0] == ""


def test_composite_keys_and_override_cols_constants():
    assert COMPOSITE_KEYS == ["캠페인 이름", "광고 세트 이름", "광고 이름"]
    assert OVERRIDE_COLS == ["brand", "판매채널", "광고목표", "소재유형", "타겟구분", "기획전명"]


def test_append_missing_rows_skips_duplicates():
    mock_ws = MagicMock()
    # 헤더 + 기존 1행
    mock_ws.get_all_values.return_value = [
        ["캠페인 이름", "광고 세트 이름", "광고 이름", "brand", "판매채널", "광고목표", "소재유형", "타겟구분", "기획전명", "비고"],
        ["캠페인A", "세트A", "광고A", "", "", "", "", "", "", ""],
    ]
    mock_gc = MagicMock()
    mock_gc.open_by_key.return_value.worksheet.return_value = mock_ws

    with patch("tools.enrich_daily.sheets_client.gspread.authorize", return_value=mock_gc), \
         patch("tools.enrich_daily.sheets_client.Credentials.from_service_account_file"):
        append_missing_rows(
            spreadsheet_id="FAKE",
            sheet_name="ad_index",
            creds_path="fake.json",
            missing_rows=[
                {"캠페인 이름": "캠페인A", "광고 세트 이름": "세트A", "광고 이름": "광고A"},  # 중복
                {"캠페인 이름": "캠페인B", "광고 세트 이름": "세트B", "광고 이름": "광고B"},  # 신규
            ],
        )

    mock_ws.append_rows.assert_called_once()
    appended = mock_ws.append_rows.call_args[0][0]
    assert len(appended) == 1
    assert appended[0][0] == "캠페인B"


def test_append_missing_rows_does_nothing_when_empty():
    with patch("tools.enrich_daily.sheets_client.gspread.authorize") as mock_auth:
        append_missing_rows("FAKE", "ad_index", "fake.json", [])
    mock_auth.assert_not_called()
