from tools.discount_checker.comparator import AdRow, CompareResult, compare


def test_exact_match_returns_일치():
    result = compare("ad_A", 70, {"uid1": 70, "uid2": 60})
    assert result.status == "일치"
    assert result.diff == 0
    assert result.representative_uid == "uid1"
    assert result.actual_max_discount == 70


def test_mismatch_creative_higher_returns_불일치():
    result = compare("ad_B", 70, {"uid1": 68})
    assert result.status == "불일치"
    assert result.diff == 2
    assert result.actual_max_discount == 68


def test_mismatch_creative_lower_returns_불일치():
    result = compare("ad_C", 60, {"uid1": 65})
    assert result.status == "불일치"
    assert result.diff == -5


def test_none_creative_discount_returns_추출불가():
    result = compare("ad_D", None, {"uid1": 70})
    assert result.status == "추출불가"
    assert result.creative_discount is None


def test_all_uids_none_returns_스크래핑실패():
    result = compare("ad_E", 70, {"uid1": None, "uid2": None})
    assert result.status == "스크래핑실패"
    assert result.actual_max_discount is None


def test_max_uid_selected_as_representative():
    result = compare("ad_F", 50, {"uid1": 30, "uid2": 50, "uid3": 40})
    assert result.representative_uid == "uid2"
    assert result.actual_max_discount == 50


def test_mixed_none_and_valid_uids_uses_valid():
    result = compare("ad_G", 70, {"uid1": None, "uid2": 70})
    assert result.status == "일치"
    assert result.representative_uid == "uid2"


def test_adrow_dataclass():
    row = AdRow(ad_name="ad_A", uids=["uid1", "uid2"])
    assert row.ad_name == "ad_A"
    assert row.uids == ["uid1", "uid2"]
