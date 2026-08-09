"""Internet Archive advanced search. No API key required."""

from __future__ import annotations

import httpx

from magmascript.domains.media.tools import (
    MediaProvider,
    MediaResult,
    MediaSearchResponse,
)

API_URL = "https://archive.org/advancedsearch.php"


class ArchiveProvider:
    """Internet Archive search."""

    @property
    def info(self) -> MediaProvider:
        return MediaProvider(
            key="archive",
            label="Archive.org",
            color="#e8637a",
            needs_key=False,
            types=["image", "video", "audio"],
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
        mediatype_map = {"video": "movies", "audio": "audio", "image": "image"}
        if media_type in mediatype_map:
            type_filter = f"mediatype:{mediatype_map[media_type]}"
        else:
            type_filter = "mediatype:(image OR movies OR audio)"

        full_query = f"{query} {type_filter}"

        params = {
            "q": full_query,
            "fl": "identifier,title,mediatype,item_size,description",
            "rows": per_page,
            "page": page,
            "output": "json",
            "sort": "downloads desc",
        }

        resp = httpx.get(API_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        docs = (data.get("response") or {}).get("docs") or []

        results = []
        for doc in docs:
            identifier = doc.get("identifier", "")
            mediatype = doc.get("mediatype", "")
            norm_type = "video" if mediatype == "movies" else "audio" if mediatype == "audio" else "image"

            results.append(MediaResult(
                id=identifier,
                title=doc.get("title") or identifier,
                thumbnail=f"https://archive.org/services/img/{identifier}",
                full_url=f"https://archive.org/services/img/{identifier}",
                source="archive",
                license="various",
                license_url="https://archive.org/about/terms.php",
                type=norm_type,
                author="",
                source_url=f"https://archive.org/details/{identifier}",
                dimensions=None,
            ))

        total = (data.get("response") or {}).get("numFound", 0)
        return MediaSearchResponse(
            results=results,
            total=total,
            page=page,
            has_more=len(docs) == per_page,
        )

    def get(self, result_id: str) -> MediaResult | None:
        return None
