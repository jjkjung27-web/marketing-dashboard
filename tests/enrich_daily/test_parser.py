import pytest
from tools.enrich_daily.parser import parse_campaign_name, PARSED_COLS

NORMAL = "26년 4월_잔스포츠_[무신사]하프파인트X뷰티 콜라보_전환_컬렉션_잠재고객/리타겟"
ALWAYS_ON = "26년 4월_잔스포츠_[무신사]월별 상시 광고_전환_카탈로그_잠재고객/리타겟"
NO_CHANNEL = "26년 4월_잔스포츠_하프파인트X뷰티 콜라보_전환_컬렉션_잠재고객"
TOO_SHORT = "26년 4월_잔스포츠_뭔가"


def test_parse_normal_campaign():
    result = parse_campaign_name(NORMAL)
    assert result["brand"] == "잔스포츠"
    assert result["판매채널"] == "무신사"
    assert result["기획전명"] == "하프파인트X뷰티 콜라보"
    assert result["광고목표"] == "전환"
    assert result["소재유형"] == "컬렉션"
    assert result["타겟구분"] == "잠재고객/리타겟"


def test_parse_always_on_campaign():
    result = parse_campaign_name(ALWAYS_ON)
    assert result["brand"] == "잔스포츠"
    assert result["판매채널"] == "무신사"
    assert result["기획전명"] == "월별 상시 광고"
    assert result["소재유형"] == "카탈로그"


def test_parse_no_channel_bracket_returns_empty_channel():
    result = parse_campaign_name(NO_CHANNEL)
    assert result["판매채널"] == ""
    assert result["기획전명"] == "하프파인트X뷰티 콜라보"


def test_parse_too_short_returns_empty_dict():
    result = parse_campaign_name(TOO_SHORT)
    assert result == {}


def test_parsed_cols_constant():
    assert PARSED_COLS == ["brand", "판매채널", "광고목표", "소재유형", "타겟구분", "기획전명"]
