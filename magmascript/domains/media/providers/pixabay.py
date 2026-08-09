"""Pixabay photos, illustrations, and video search. Requires API key."""

from __future__ import annotations

import httpx

from magmascript.domains.media.tools import (
    MediaDimensions,
    MediaProvider,
    MediaResult,
    MediaSearchResponse,
)

API_PHOTOS = "https://pixabay.com/api/"
API_VIDEOS = "https://pixabay.com/api/videos/"


class PixabayProvider:
    """Pixabay media search."""

    def __init__(self, api_key: str = ""):
        self._key = api_key

    @property
    def info(self) -> MediaProvider:
        return MediaProvider(
            key="pixabay",
            label="Pixabay",
            color="#4dc9f6",
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
        endpoint = API_VIDEOS if is_video else API_PHOTOS

        params: dict = {
            "key": self._key,
            "q": query,
            "page": page,
            "per_page": per_page,
            "safesearch": "true",
        }
        if not is_video and orientation:
            params["orientation"] = orientation

        resp = httpx.get(endpoint, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = []
        if is_video:
            for v in data.get("hits", []):
                vid = (v.get("videos") or {}).get("medium") or (v.get("videos") or {}).get("small") or {}
                dim = None
                size_str = vid.get("size", "")
                if "x" in size_str:
                    parts = size_str.split("x")
                    try:
                        dim = MediaDimensions(width=int(parts[0]), height=int(parts[1]))
                    except ValueError:
                        pass
                picture_id = v.get("picture_id", "")
                results.append(MediaResult(
                    id=str(v.get("id", "")),
                    title=v.get("tags") or "Video",
                    thumbnail=f"https://i.vimeocdn.com/video/{picture_id}_640x360.jpg" if picture_id else "",
                    full_url=vid.get("url") or "",
                    source="pixabay",
                    license="free-commercial",
                    license_url="https://pixabay.com/service/license-summary/",
                    type="video",
                    author=v.get("user") or "",
                    source_url=v.get("pageURL") or "",
                    dimensions=dim,
                ))
        else:
            for p in data.get("hits", []):
                dim = None
                if p.get("imageWidth") and p.get("imageHeight"):
                    dim = MediaDimensions(width=p["imageWidth"], height=p["imageHeight"])
                results.append(MediaResult(
                    id=str(p.get("id", "")),
                    title=p.get("tags") or "Image",
                    thumbnail=p.get("webformatURL") or "",
                    full_url=p.get("largeImageURL") or p.get("fullHDURL") or p.get("webformatURL") or "",
                    source="pixabay",
                    license="free-commercial",
                    license_url="https://pixabay.com/service/license-summary/",
                    type="image",
                    author=p.get("user") or "",
                    source_url=p.get("pageURL") or "",
                    dimensions=dim,
                ))

        return MediaSearchResponse(
            results=results,
            total=data.get("totalHits", 0),
            page=page,
            has_more=len(results) == per_page,
        )

    def get(self, result_id: str) -> MediaResult | None:
        return None
