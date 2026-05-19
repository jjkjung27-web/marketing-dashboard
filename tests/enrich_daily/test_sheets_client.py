from unittest.mock import patch, MagicMock
import pandas as pd
from tools.enrich_daily.sheets_client import load_index, COMPOSITE_KEYS, OVERRIDE_COLS

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
