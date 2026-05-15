from unittest.mock import patch, MagicMock
import pandas as pd
from budget_check.loaders.kakao_loader import fetch_kakao_spend

KAKAO_RESPONSE = {
    "data": [
        {
            "dimensions": {"campaignName": "캠페인B", "adGroupName": "그룹2"},
            "metrics": {"cost": 500000}
        },
        {
            "dimensions": {"campaignName": "캠페인D", "adGroupName": "그룹4"},
            "metrics": {"cost": 300000}
        }
    ]
}

def test_fetch_kakao_spend_returns_expected_columns():
    with patch("budget_check.loaders.kakao_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = KAKAO_RESPONSE
        df = fetch_kakao_spend("token", "acc123", "2026-05-15")
    assert list(df.columns) == ["매체", "캠페인", "그룹", "api_소진"]

def test_fetch_kakao_spend_sets_media_name():
    with patch("budget_check.loaders.kakao_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = KAKAO_RESPONSE
        df = fetch_kakao_spend("token", "acc123", "2026-05-15")
    assert (df["매체"] == "Kakao").all()

def test_fetch_kakao_spend_correct_values():
    with patch("budget_check.loaders.kakao_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = KAKAO_RESPONSE
        df = fetch_kakao_spend("token", "acc123", "2026-05-15")
    row = df[df["그룹"] == "그룹2"]
    assert row["api_소진"].iloc[0] == 500000

def test_fetch_kakao_spend_empty_response():
    with patch("budget_check.loaders.kakao_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = {"data": []}
        df = fetch_kakao_spend("token", "acc123", "2026-05-15")
    assert df.empty
