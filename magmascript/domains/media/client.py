"""Media domain — multi-provider media search client.

Surfaces provider errors in MediaSearchResponse.errors.
Caches search results for faster repeated queries.
"""

from __future__ import annotations

import concurrent.futures
from dataclasses import asdict
from typing import Any

from magmascript.core.cache import CacheStore, get_cache
from magmascript.core.config import Config, get_config
from magmascript.domains.media.tools import (
    MediaDimensions,
    MediaProvider,
    MediaResult,
    MediaSearchResponse,
)
from magmascript.domains.media.providers.openverse import OpenverseProvider
from magmascript.domains.media.providers.pexels import PexelsProvider
from magmascript.domains.media.providers.pixabay import PixabayProvider
from magmascript.domains.media.providers.met_museum import MetMuseumProvider
from magmascript.domains.media.providers.smithsonian import SmithsonianProvider
from magmascript.domains.media.providers.archive import ArchiveProvider

DEFAULT_PROVIDERS = ["openverse", "pexels", "pixabay", "met_museum", "smithsonian", "archive"]


def _serialize_response(resp: MediaSearchResponse) -> dict:
    """Convert MediaSearchResponse to JSON-safe dict."""
    return {
        "results": [asdict(r) for r in resp.results],
        "total": resp.total,
        "page": resp.page,
        "has_more": resp.has_more,
        "provider_totals": resp.provider_totals,
        "errors": resp.errors,
    }


def _deserialize_response(data: dict) -> MediaSearchResponse:
    """Reconstruct MediaSearchResponse from dict."""
    results = []
    for r in data.get("results", []):
        dim = r.get("dimensions")
        if dim and isinstance(dim, dict):
            dim = MediaDimensions(**dim)
        results.append(MediaResult(
            id=r["id"],
            title=r["title"],
            thumbnail=r["thumbnail"],
            full_url=r["full_url"],
            source=r["source"],
            license=r["license"],
            license_url=r["license_url"],
            type=r["type"],
            author=r["author"],
            source_url=r["source_url"],
            dimensions=dim,
        ))
    return MediaSearchResponse(
        results=results,
        total=data.get("total", 0),
        page=data.get("page", 1),
        has_more=data.get("has_more", False),
        provider_totals=data.get("provider_totals", {}),
        errors=data.get("errors", {}),
    )


class MediaClient:
    """Multi-provider media search client.

    Fans out queries to all enabled providers, normalizes and merges results.
    One provider failing does not break the others — errors are surfaced
    in MediaSearchResponse.errors.
    """

    def __init__(self, config: Config | None = None, *, providers: list[str] | None = None):
        cfg = config or get_config()
        self._providers_enabled = providers or DEFAULT_PROVIDERS
        self._providers: dict[str, Any] = {}
        self._cache = get_cache(enabled=cfg.cache.enabled)
        self._cache_ttl = cfg.cache.ttl_media

        key_map = {"pexels": cfg.media.pexels_key, "pixabay": cfg.media.pixabay_key}
        provider_classes = {
            "openverse": OpenverseProvider,
            "pexels": PexelsProvider,
            "pixabay": PixabayProvider,
            "met_museum": MetMuseumProvider,
            "smithsonian": SmithsonianProvider,
            "archive": ArchiveProvider,
        }

        for key in self._providers_enabled:
            cls = provider_classes.get(key)
            if cls is None:
                continue
            if key in ("pexels", "pixabay"):
                self._providers[key] = cls(api_key=key_map.get(key, ""))
            else:
                self._providers[key] = cls()

    def list_providers(self) -> list[MediaProvider]:
        """List all registered providers with their metadata."""
        return [p.info for p in self._providers.values()]

    def search(
        self,
        query: str,
        *,
        source: str = "",
        media_type: str = "",
        orientation: str = "",
        page: int = 1,
        per_page: int = 24,
        use_cache: bool = True,
    ) -> MediaSearchResponse:
        """Search across all enabled providers (or a specific source).

        Provider errors are collected in MediaSearchResponse.errors.
        Results are cached for repeated queries.
        """
        # Check cache
        cache_key = CacheStore.make_key(
            "search", q=query, src=source, type=media_type,
            orient=orientation, page=page, pp=per_page,
        )
        if use_cache:
            cached = self._cache.get("media", cache_key)
            if cached is not None:
                return _deserialize_response(cached)

        # Fan out to providers
        targets = [source] if source and source in self._providers else list(self._providers.keys())

        def _search_one(key: str) -> tuple[str, MediaSearchResponse | None, str]:
            try:
                provider = self._providers[key]
                result = provider.search(
                    query, page=page, per_page=per_page,
                    media_type=media_type, orientation=orientation,
                )
                return key, result, ""
            except Exception as e:
                return key, None, str(e)

        merged_results = []
        total = 0
        has_more = False
        provider_totals = {}
        errors = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(_search_one, key): key for key in targets}
            for future in concurrent.futures.as_completed(futures):
                key, result, error = future.result()
                if result is None:
                    errors[key] = error or "unknown error"
                    continue
                merged_results.extend(result.results)
                total += result.total
                provider_totals[key] = result.total
                if result.has_more:
                    has_more = True

        response = MediaSearchResponse(
            results=merged_results,
            total=total,
            page=page,
            has_more=has_more,
            provider_totals=provider_totals,
            errors=errors,
        )

        # Store in cache
        if use_cache:
            self._cache.set("media", cache_key, _serialize_response(response), ttl=self._cache_ttl)

        return response

    def get(self, result_id: str, source: str) -> MediaResult | None:
        """Get a single result by ID from a specific provider."""
        provider = self._providers.get(source)
        if provider is None:
            return None
        try:
            return provider.get(result_id)
        except Exception:
            return None

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
