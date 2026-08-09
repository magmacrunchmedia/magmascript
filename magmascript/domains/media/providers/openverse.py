"""Openverse (WordPress) CC-licensed media search. No API key required."""

from __future__ import annotations

import httpx

from magmascript.domains.media.tools import (
    MediaDimensions,
    MediaProvider,
    MediaResult,
    MediaSearchResponse,
)

API_BASE = "https://api.openverse.org/v1"


class OpenverseProvider:
    """Openverse media search."""

    @property
    def info(self) -> MediaProvider:
        return MediaProvider(
            key="openverse",
            label="Openverse",
            color="#a78bfa",
            needs_key=False,
            types=["image", "audio", "video"],
        )

    def search(
        self,
        query: str,
        *,
        page: int = 1,
        per_page: int = 24,
        media_type: str = "",
        orientation: str = "",
    ) -> MediaSearchResponse:
        endpoint_type = "images"
        if media_type == "video":
            endpoint_type = "video"
        elif media_type == "audio":
            endpoint_type = "audio"

        params: dict = {
            "q": query,
            "page": page,
            "page_size": per_page,
            "format": "json",
        }

        orientation_map = {"horizontal": "landscape", "vertical": "portrait", "square": "square"}
        if orientation in orientation_map:
            params["aspect_ratio"] = orientation_map[orientation]

        resp = httpx.get(f"{API_BASE}/{endpoint_type}/", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for r in data.get("results", []):
            dim = None
            if r.get("dimensions"):
                dim = MediaDimensions(
                    width=r["dimensions"].get("width", 0),
                    height=r["dimensions"].get("height", 0),
                )
            results.append(MediaResult(
                id=str(r.get("id", "")),
                title=r.get("title") or "Untitled",
                thumbnail=r.get("thumbnail") or r.get("url") or "",
                full_url=r.get("url") or r.get("original") or "",
                source="openverse",
                license=r.get("license") or r.get("license_version") or "",
                license_url=r.get("license_url") or "",
                type=r.get("media_type", "image"),
                author=r.get("creator") or "",
                source_url=r.get("foreign_landing_url") or r.get("detail_url") or "",
                dimensions=dim,
            ))

        return MediaSearchResponse(
            results=results,
            total=data.get("result_count", 0),
            page=page,
            has_more=len(results) == per_page,
        )

    def get(self, result_id: str) -> MediaResult | None:
        return None
