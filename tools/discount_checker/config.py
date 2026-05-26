import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

META_ACCESS_TOKEN: str = os.environ["META_ACCESS_TOKEN"]
META_AD_ACCOUNT_ID: str = os.environ["META_AD_ACCOUNT_ID"]
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
SLACK_WEBHOOK_URL: str = os.environ.get("SLACK_WEBHOOK_URL", "")

CACHE_PATH = Path("cache/discount_check_cache.json")
OUTPUT_DIR = Path("output")
