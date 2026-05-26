import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)


def _get(key: str, default: str | None = None) -> str:
    """Streamlit Cloud secrets → 로컬 .env 순으로 값을 읽는다."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    val = os.environ.get(key, "")
    if default is None and not val:
        raise KeyError(f"환경변수 '{key}'가 설정되지 않았습니다. .env 또는 Streamlit secrets를 확인하세요.")
    return val or default or ""


META_ACCESS_TOKEN: str = _get("META_ACCESS_TOKEN")
META_AD_ACCOUNT_ID: str = _get("META_AD_ACCOUNT_ID")
ANTHROPIC_API_KEY: str = _get("ANTHROPIC_API_KEY")
SLACK_WEBHOOK_URL: str = _get("SLACK_WEBHOOK_URL", default="")

CACHE_PATH = Path("cache/discount_check_cache.json")
OUTPUT_DIR = Path("output")
