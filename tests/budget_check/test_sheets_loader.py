from unittest.mock import patch, MagicMock
import pandas as pd
import io
from budget_check.loaders.sheets_loader import parse_sheets_url, load_budget_plan

def test_parse_sheets_url_extracts_id_and_gid():
    url = "https://docs.google.com/spreadsheets/d/1FvRdm-E8kxJy/edit?gid=1367713947#gid=1367713947"
    sheet_id, gid = parse_sheets_url(url)
    assert sheet_id == "1FvRdm-E8kxJy"
    assert gid == "1367713947"

def test_parse_sheets_url_no_gid_defaults_to_zero():
    url = "https://docs.google.com/spreadsheets/d/1FvRdm-E8kxJy/edit"
    sheet_id, gid = parse_sheets_url(url)
    assert sheet_id == "1FvRdm-E8kxJy"
    assert gid == "0"

PLAN_CSV = """날짜,매체,캠페인,그룹,일예산
2026-05-15,Meta,캠페인A,그룹1,1200000
2026-05-15,Kakao,캠페인B,그룹2,400000
2026-05-14,Meta,캠페인A,그룹1,1000000
"""

def test_load_budget_plan_filters_by_date():
    with patch("budget_check.loaders.sheets_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=PLAN_CSV)
        df = load_budget_plan("https://docs.google.com/spreadsheets/d/FAKE/edit?gid=0", date="2026-05-15")
    assert len(df) == 2

def test_load_budget_plan_returns_expected_columns():
    with patch("budget_check.loaders.sheets_loader.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=PLAN_CSV)
        df = load_budget_plan("https://docs.google.com/spreadsheets/d/FAKE/edit?gid=0", date="2026-05-15")
    assert list(df.columns) == ["매체", "캠페인", "그룹", "일예산"]
