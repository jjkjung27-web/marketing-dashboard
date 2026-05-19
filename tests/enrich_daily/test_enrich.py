import io
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from tools.enrich_daily.enrich import add_date_columns, add_parsed_columns, apply_overrides, get_parse_failures

RAW_ROWS = [
    {
        "연월": "2026-05",
        "날짜": "2026-05-05",
        "media": "메타",
        "캠페인 이름": "26년 4월_잔스포츠_[무신사]하프파인트X뷰티 콜라보_전환_컬렉션_잠재고객/리타겟",
        "광고 세트 이름": "컬렉션_[무신사]하프파인트X뷰티콜라보_잠재고객_1865+_남여",
        "광고 이름": "컬렉션6",
    },
    {
        "연월": "2026-05",
        "날짜": "2026-05-05",
        "media": "메타",
        "캠페인 이름": "파싱실패_이름",  # 6 파트 미만 → 파싱 실패
        "광고 세트 이름": "세트X",
        "광고 이름": "광고X",
    },
]


@pytest.fixture
def raw_df():
    return pd.DataFrame(RAW_ROWS)


def test_add_date_columns(raw_df):
    df = add_date_columns(raw_df)
    assert df["weeknum"].iloc[0] == 19   # 2026-05-05는 ISO week 19 (월요일 기준)
    assert df["연월"].iloc[0] == "2026-05"


def test_add_parsed_columns(raw_df):
    df = add_parsed_columns(raw_df)
    assert df["brand"].iloc[0] == "잔스포츠"
    assert df["판매채널"].iloc[0] == "무신사"
    assert df["광고목표"].iloc[0] == "전환"
    assert df["소재유형"].iloc[0] == "컬렉션"
    assert df["타겟구분"].iloc[0] == "잠재고객/리타겟"
    assert df["기획전명"].iloc[0] == "하프파인트X뷰티 콜라보"
    # 파싱 실패 행은 빈 문자열
    assert df["brand"].iloc[1] == ""


def test_apply_overrides(raw_df):
    df = add_parsed_columns(raw_df)
    index_df = pd.DataFrame([{
        "캠페인 이름": "26년 4월_잔스포츠_[무신사]하프파인트X뷰티 콜라보_전환_컬렉션_잠재고객/리타겟",
        "광고 세트 이름": "컬렉션_[무신사]하프파인트X뷰티콜라보_잠재고객_1865+_남여",
        "광고 이름": "컬렉션6",
        "brand": "JanSport",   # 오버라이드
        "판매채널": "",         # 비어있음 → 파싱값 유지
        "광고목표": "", "소재유형": "", "타겟구분": "", "기획전명": "",
    }])
    result = apply_overrides(df, index_df)
    assert result["brand"].iloc[0] == "JanSport"
    assert result["판매채널"].iloc[0] == "무신사"   # 빈 오버라이드 → 파싱값 유지


def test_get_parse_failures(raw_df):
    df = add_parsed_columns(raw_df)
    failures = get_parse_failures(df)
    assert len(failures) == 1
    assert failures[0]["캠페인 이름"] == "파싱실패_이름"
    assert failures[0]["광고 이름"] == "광고X"
