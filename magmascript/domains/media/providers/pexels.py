"""Pexels photos and video search. Requires API key (free at pexels.com/api)."""

from __future__ import annotations

import httpx

from magmascript.domains.media.tools import (
    MediaDimensions,
    MediaProvider,
    MediaResult,
    MediaSearchResponse,
)

API_BASE = "https://api.pexels.com/v1"


class PexelsProvider:
    """Pexels media search."""

    def __init__(self, api_key: str = ""):
        self._key = api_key

    @property
    def info(self) -> MediaProvider:
        return MediaProvider(
            key="pexels",
            label="Pexels",
            color="#2ee8a5",
            needs_key=True,
            types=["image", "video"],
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
        if not self._key:
            return MediaSearchResponse(results=[], total=0, page=page, has_more=False)

        is_video = media_type == "video"
        endpoint = f"{API_BASE}/videos/search" if is_video else f"{API_BASE}/search"

        params: dict = {"query": query, "page": page, "per_page": per_page}
        if not is_video and orientation:
            params["orientation"] = orientation

        resp = httpx.get(endpoint, params=params, headers={"Authorization": self._key}, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = []
        if is_video:
            for v in data.get("videos", []):
                dim = None
                if v.get("width") and v.get("height"):
                    dim = MediaDimensions(width=v["width"], height=v["height"])
                user = v.get("user") or {}
                pics = v.get("video_pictures") or [{}]
                files = v.get("video_files") or [{}]
                results.append(MediaResult(
                    id=str(v.get("id", "")),
                    title=user.get("name") or "Video",
                    thumbnail=pics[0].get("image", ""),
                    full_url=files[0].get("link", ""),
                    source="pexels",
                    license="free-commercial",
                    license_url="https://www.pexels.com/license/",
                    type="video",
                    author=user.get("name") or "",
                    source_url=v.get("url") or "",
                    dimensions=dim,
                ))
        else:
            for p in data.get("photos", []):
                dim = None
                if p.get("width") and p.get("height"):
                    dim = MediaDimensions(width=p["width"], height=p["height"])
                src = p.get("src") or {}
                results.append(MediaResult(
                    id=str(p.get("id", "")),
                    title=p.get("alt") or "Photo",
                    thumbnail=src.get("medium") or src.get("small") or "",
                    full_url=src.get("original") or "",
                    source="pexels",
                    license="free-commercial",
                    license_url="https://www.pexels.com/license/",
                    type="image",
                    author=p.get("photographer") or "",
                    source_url=p.get("url") or "",
                    dimensions=dim,
                ))

        return MediaSearchResponse(
            results=results,
            total=data.get("total_results", 0),
            page=page,
            has_more=len(results) == per_page,
        )

    def get(self, result_id: str) -> MediaResult | None:
        return None
