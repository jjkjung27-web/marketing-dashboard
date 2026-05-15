from unittest.mock import patch, MagicMock
import pandas as pd
from budget_check.slack_sender import format_message, send_to_slack

VALIDATION_DF = pd.DataFrame([
    {"매체": "Meta", "캠페인": "캠페인A", "그룹": "그룹1", "rd_소진": 1000000, "api_소진": 998000, "차이": -2000, "상태": "🟢 허용 오차"},
    {"매체": "Kakao", "캠페인": "캠페인B", "그룹": "그룹2", "rd_소진": 500000, "api_소진": 500000, "차이": 0, "상태": "✅ 일치"},
])

BUDGET_DF = pd.DataFrame([
    {"매체": "Meta", "캠페인": "캠페인A", "그룹": "그룹1", "일예산": 1200000, "소진": 998000, "차이": -202000, "상태": "🔴 미소진"},
    {"매체": "Kakao", "캠페인": "캠페인B", "그룹": "그룹2", "일예산": 400000, "소진": 500000, "차이": 100000, "상태": "🟡 과소진"},
])

def test_format_message_contains_date():
    msg = format_message("2026-05-15", VALIDATION_DF, BUDGET_DF)
    assert "2026-05-15" in msg

def test_format_message_contains_overspend():
    msg = format_message("2026-05-15", VALIDATION_DF, BUDGET_DF)
    assert "과소진" in msg
    assert "캠페인B" in msg

def test_format_message_contains_underspend():
    msg = format_message("2026-05-15", VALIDATION_DF, BUDGET_DF)
    assert "미소진" in msg
    assert "캠페인A" in msg

def test_format_message_contains_total():
    msg = format_message("2026-05-15", VALIDATION_DF, BUDGET_DF)
    assert "1,600,000" in msg  # 일예산 합계

def test_send_to_slack_posts_to_webhook():
    with patch("budget_check.slack_sender.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        send_to_slack("https://hooks.slack.com/test", "테스트 메시지")
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs[1]["json"]["text"] == "테스트 메시지"
