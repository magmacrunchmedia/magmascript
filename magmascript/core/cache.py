"""File-based cache with TTL expiration.

Storage: ~/.cache/magmascript/{domain}/{key_hash}.json
Each entry: {"data": <any>, "expires": <epoch_float>}
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


# Default TTLs in seconds per domain
DEFAULT_TTLS: dict[str, int] = {
    "media": 86400,  # 24 hours
    "scores": 3600,  # 1 hour
    "gh": 300,  # 5 minutes
}

CACHE_DIR = Path.home() / ".cache" / "magmascript"


class CacheStats:
    """Lightweight stats counter (in-memory, not persisted)."""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.errors = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


class CacheStore:
    """File-based key-value cache with per-domain TTL.

    Usage:
        cache = CacheStore()
        cache.set("media", "search:art:1", {"results": [...]}, ttl=86400)
        data = cache.get("media", "search:art:1")
    """

    def __init__(self, cache_dir: Path | None = None, *, enabled: bool = True):
        self._dir = cache_dir or CACHE_DIR
        self._enabled = enabled
        self._stats = CacheStats()

    @property
    def stats(self) -> CacheStats:
        return self._stats

    def _key_path(self, domain: str, key: str) -> Path:
        """Compute file path for a cache key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        domain_dir = self._dir / domain
        return domain_dir / f"{key_hash}.json"

    @staticmethod
    def make_key(operation: str, **kwargs: Any) -> str:
        """Build a deterministic cache key from operation name and args.

        Args:
            operation: e.g. "search", "get_scores"
            **kwargs: Function arguments (must be JSON-serializable)

        Returns:
            A string key like "search:query=art:page=1:per_page=24"
        """
        parts = [operation]
        for k, v in sorted(kwargs.items()):
            if v is not None and v != "" and v != 0:
                parts.append(f"{k}={v}")
        return ":".join(parts)

    def get(self, domain: str, key: str) -> Any | None:
        """Get a cached value. Returns None if missing or expired."""
        if not self._enabled:
            self._stats.misses += 1
            return None

        path = self._key_path(domain, key)
        if not path.is_file():
            self._stats.misses += 1
            return None

        try:
            raw = json.loads(path.read_text())
            if time.time() > raw["expires"]:
                path.unlink(missing_ok=True)
                self._stats.misses += 1
                return None
            self._stats.hits += 1
            return raw["data"]
        except (json.JSONDecodeError, KeyError, OSError):
            path.unlink(missing_ok=True)
            self._stats.errors += 1
            self._stats.misses += 1
            return None

    def set(self, domain: str, key: str, data: Any, *, ttl: int | None = None) -> None:
        """Store a value with TTL. Uses atomic write (tmp + rename)."""
        if not self._enabled:
            return

        if ttl is None:
            ttl = DEFAULT_TTLS.get(domain, 3600)

        path = self._key_path(domain, key)
        path.parent.mkdir(parents=True, exist_ok=True)

        entry = {
            "data": data,
            "expires": time.time() + ttl,
        }

        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(entry, default=str))
            tmp.rename(path)
            self._stats.sets += 1
        except OSError:
            tmp.unlink(missing_ok=True)
            self._stats.errors += 1

    def clear(self, *, domain: str | None = None) -> int:
        """Delete cache entries. Returns count of files removed."""
        count = 0
        if domain:
            target = self._dir / domain
            if target.is_dir():
                for f in target.glob("*.json"):
                    f.unlink(missing_ok=True)
                    count += 1
        else:
            if self._dir.is_dir():
                for domain_dir in self._dir.iterdir():
                    if domain_dir.is_dir():
                        for f in domain_dir.glob("*.json"):
                            f.unlink(missing_ok=True)
                            count += 1
        return count

    def file_stats(self) -> dict[str, Any]:
        """Get on-disk cache statistics."""
        result: dict[str, Any] = {
            "total_files": 0,
            "total_size_bytes": 0,
            "domains": {},
            "enabled": self._enabled,
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "sets": self._stats.sets,
            "hit_rate": f"{self._stats.hit_rate:.1%}",
        }

        if not self._dir.is_dir():
            return result

        for domain_dir in sorted(self._dir.iterdir()):
            if not domain_dir.is_dir():
                continue
            files = list(domain_dir.glob("*.json"))
            size = sum(f.stat().st_size for f in files)
            result["domains"][domain_dir.name] = {
                "files": len(files),
                "size_bytes": size,
            }
            result["total_files"] += len(files)
            result["total_size_bytes"] += size

        return result


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_cache: CacheStore | None = None


def get_cache(*, enabled: bool = True) -> CacheStore:
    """Get the global cache singleton."""
    global _cache
    if _cache is None:
        _cache = CacheStore(enabled=enabled)
    return _cache
