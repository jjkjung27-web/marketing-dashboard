import time
from tools.discount_checker.cache import Cache, CACHE_MISS


def test_miss_returns_cache_miss_sentinel(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    assert cache.get("missing") is CACHE_MISS


def test_set_and_get(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    cache.set("key1", 70)
    assert cache.get("key1") == 70


def test_set_none_is_distinguishable_from_miss(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    cache.set("key1", None)
    result = cache.get("key1")
    assert result is not CACHE_MISS
    assert result is None


def test_ttl_expiry(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    cache.set("key2", 50, ttl_seconds=1)
    assert cache.get("key2") == 50
    time.sleep(1.1)
    assert cache.get("key2") is CACHE_MISS


def test_permanent_entry_survives(tmp_path):
    cache = Cache(tmp_path / "cache.json")
    cache.set("key3", 30, ttl_seconds=None)
    time.sleep(0.1)
    assert cache.get("key3") == 30


def test_persists_across_instances(tmp_path):
    path = tmp_path / "cache.json"
    Cache(path).set("key4", 99)
    assert Cache(path).get("key4") == 99
