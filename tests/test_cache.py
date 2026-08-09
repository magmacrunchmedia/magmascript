"""Tests for the file-based cache."""

import json
import time
from pathlib import Path

import pytest

from magmascript.core.cache import CacheStore, get_cache


@pytest.fixture
def tmp_cache(tmp_path):
    return CacheStore(cache_dir=tmp_path)


class TestCacheStore:
    def test_set_and_get(self, tmp_cache):
        tmp_cache.set("test", "key1", {"hello": "world"})
        assert tmp_cache.get("test", "key1") == {"hello": "world"}

    def test_get_missing(self, tmp_cache):
        assert tmp_cache.get("test", "nope") is None

    def test_ttl_expiration(self, tmp_cache):
        tmp_cache.set("test", "key1", "data", ttl=0)
        time.sleep(0.01)
        assert tmp_cache.get("test", "key1") is None

    def test_clear_domain(self, tmp_cache):
        tmp_cache.set("a", "k1", 1)
        tmp_cache.set("b", "k2", 2)
        count = tmp_cache.clear(domain="a")
        assert count == 1
        assert tmp_cache.get("a", "k1") is None
        assert tmp_cache.get("b", "k2") == 2

    def test_clear_all(self, tmp_cache):
        tmp_cache.set("a", "k1", 1)
        tmp_cache.set("b", "k2", 2)
        count = tmp_cache.clear()
        assert count == 2
        assert tmp_cache.get("a", "k1") is None
        assert tmp_cache.get("b", "k2") is None

    def test_make_key_deterministic(self):
        k1 = CacheStore.make_key("search", q="art", page=1)
        k2 = CacheStore.make_key("search", q="art", page=1)
        assert k1 == k2

    def test_make_key_ignores_empty(self):
        k1 = CacheStore.make_key("search", q="art", page=1)
        k2 = CacheStore.make_key("search", q="art", page=1, source="")
        assert k1 == k2

    def test_disabled_cache(self, tmp_cache):
        tmp_cache._enabled = False
        tmp_cache.set("test", "k1", "v1")
        assert tmp_cache.get("test", "k1") is None

    def test_file_stats(self, tmp_cache):
        tmp_cache.set("media", "k1", "v1")
        tmp_cache.set("scores", "k2", "v2")
        stats = tmp_cache.file_stats()
        assert stats["total_files"] == 2
        assert "media" in stats["domains"]
        assert "scores" in stats["domains"]

    def test_corrupt_file_returns_none(self, tmp_cache):
        path = tmp_cache._key_path("test", "k1")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not json!!!")
        assert tmp_cache.get("test", "k1") is None

    def test_stats_counting(self, tmp_cache):
        tmp_cache.set("test", "k1", "v1")
        tmp_cache.get("test", "k1")  # hit
        tmp_cache.get("test", "k2")  # miss
        s = tmp_cache.stats
        assert s.hits == 1
        assert s.misses == 1
        assert s.sets == 1
