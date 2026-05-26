import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

META_ACCESS_TOKEN: str = os.environ["META_ACCESS_TOKEN"]
META_AD_ACCOUNT_ID: str = os.environ["META_AD_ACCOUNT_ID"]
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
SLACK_WEBHOOK_URL: str = os.environ.get("SLACK_WEBHOOK_URL", "")
GOOGLE_SERVICE_ACCOUNT_JSON: str = os.environ.get(
    "GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json"
)

CACHE_PATH = Path("cache/discount_check_cache.json")
OUTPUT_DIR = Path("output")
