from unittest.mock import patch, MagicMock
import pandas as pd
from budget_check.loaders.meta_loader import fetch_meta_spend

META_RESPONSE = {
    "data": [
        {"campaign_name": "캠페인A", "adset_name": "그룹1", "spend": "998.00"},
        {"campaign_name": "캠페인C", "adset_name": "그룹3", "spend": "300.00"},
    ],
    "paging": {}
}

def test_fetch_meta_spend_returns_expected_columns():
    with patch("budget_check.loaders.meta_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = META_RESPONSE
        df = fetch_meta_spend("token", "123456", "2026-05-15")
    assert list(df.columns) == ["매체", "캠페인", "그룹", "api_소진"]

def test_fetch_meta_spend_sets_media_name():
    with patch("budget_check.loaders.meta_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = META_RESPONSE
        df = fetch_meta_spend("token", "123456", "2026-05-15")
    assert (df["매체"] == "Meta").all()

def test_fetch_meta_spend_converts_spend_to_int():
    with patch("budget_check.loaders.meta_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = META_RESPONSE
        df = fetch_meta_spend("token", "123456", "2026-05-15")
    assert df["api_소진"].dtype == "int64"
    assert df.iloc[0]["api_소진"] == 998

def test_fetch_meta_spend_empty_response():
    with patch("budget_check.loaders.meta_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = {"data": [], "paging": {}}
        df = fetch_meta_spend("token", "123456", "2026-05-15")
    assert df.empty
