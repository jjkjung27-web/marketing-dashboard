import pytest
from unittest.mock import patch, MagicMock
from tools.discount_checker.sheet_reader import parse_sheets_url, _find_header_indices, _parse_uid_list


def test_parse_spreadsheet_id():
    url = "https://docs.google.com/spreadsheets/d/16kWSflx6xgn_VixO-tQoFylvJ2L85TdfX665MNFQw0A/edit#gid=288639799"
    sid, gid, range_str = parse_sheets_url(url)
    assert sid == "16kWSflx6xgn_VixO-tQoFylvJ2L85TdfX665MNFQw0A"


def test_parse_gid():
    url = "https://docs.google.com/spreadsheets/d/16kWSflx6xgn_VixO-tQoFylvJ2L85TdfX665MNFQw0A/edit#gid=288639799"
    sid, gid, range_str = parse_sheets_url(url)
    assert gid == "288639799"


def test_parse_range_from_fragment():
    url = "https://docs.google.com/spreadsheets/d/ABC/edit#gid=123&range=A1:Z100"
    sid, gid, range_str = parse_sheets_url(url)
    assert range_str == "A1:Z100"


def test_parse_no_range_returns_none():
    url = "https://docs.google.com/spreadsheets/d/ABC/edit#gid=123"
    sid, gid, range_str = parse_sheets_url(url)
    assert range_str is None


def test_invalid_url_raises():
    with pytest.raises(ValueError, match="Invalid Google Sheets URL"):
        parse_sheets_url("https://example.com/not-a-sheet")


def test_find_header_indices_success():
    rows = [
        [],
        ["", "캠페인", "광고명", "담당", "UID"],
        ["", "캠1", "ad_A", "담당자", "uid1, uid2"],
    ]
    ad_idx, uid_idx, header_row_idx = _find_header_indices(rows, "광고명", "UID")
    assert ad_idx == 2
    assert uid_idx == 4
    assert header_row_idx == 1


def test_find_header_indices_missing_ad_col():
    rows = [["캠페인", "그룹", "UID"]]
    with pytest.raises(ValueError, match="광고명"):
        _find_header_indices(rows, "광고명", "UID")


def test_find_header_indices_missing_uid_col():
    rows = [["광고명", "캠페인"]]
    with pytest.raises(ValueError, match="UID"):
        _find_header_indices(rows, "광고명", "UID")


def test_parse_uid_list_comma_separated():
    result = _parse_uid_list("4944027, 3825639, 3752602")
    assert result == ["4944027", "3825639", "3752602"]


def test_parse_uid_list_single():
    result = _parse_uid_list("5877083")
    assert result == ["5877083"]


def test_parse_uid_list_with_parentheses_in_note():
    result = _parse_uid_list("4167495, 3727165(껌정), 2384820(그린)")
    assert result == ["4167495", "3727165", "2384820"]
