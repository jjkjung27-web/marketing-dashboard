import json
import time
from pathlib import Path
from typing import Any

CACHE_MISS = object()


class Cache:
    def __init__(self, path: Path):
        self._path = Path(path)
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            return json.loads(self._path.read_text(encoding="utf-8"))
        return {}

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get(self, key: str) -> Any:
        entry = self._data.get(key)
        if entry is None:
            return CACHE_MISS
        if entry.get("expires_at") and time.time() > entry["expires_at"]:
            del self._data[key]
            self._save()
            return CACHE_MISS
        return entry["value"]

    def set(self, key: str, value: Any, ttl_seconds: int | None = None):
        self._data[key] = {
            "value": value,
            "expires_at": time.time() + ttl_seconds if ttl_seconds else None,
        }
        self._save()
