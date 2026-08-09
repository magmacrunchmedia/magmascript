"""Smithsonian Open Access API. Uses DEMO_KEY (rate limited)."""

from __future__ import annotations

import httpx

from magmascript.domains.media.tools import (
    MediaProvider,
    MediaResult,
    MediaSearchResponse,
)

API_URL = "https://api.si.edu/openaccess/api/v1.0/search"


class SmithsonianProvider:
    """Smithsonian Open Access search."""

    @property
    def info(self) -> MediaProvider:
        return MediaProvider(
            key="smithsonian",
            label="Smithsonian",
            color="#f4845f",
            needs_key=False,
            types=["image"],
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
        start = (page - 1) * per_page
        params = {"q": query, "rows": per_page, "start": start, "api_key": "DEMO_KEY"}

        resp = httpx.get(API_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        rows = (data.get("response") or {}).get("rows") or []

        results = []
        for r in rows:
            content = r.get("content") or {}
            desc = content.get("descriptiveNonRepeating") or {}
            index = content.get("indexedStructured") or {}
            media = (desc.get("online_media") or {}).get("media") or []
            primary = desc.get("primaryMedia") or []

            img = ""
            thumb = ""
            if media:
                img = media[0].get("content") or ""
                thumb = media[0].get("thumbnail") or img
            elif primary:
                img = primary[0] if isinstance(primary[0], str) else ""
                thumb = img

            if not thumb:
                continue

            names = index.get("name") or []
            title = desc.get("title")
            if isinstance(title, dict):
                title = title.get("content", "Untitled")

            results.append(MediaResult(
                id=str(r.get("id") or desc.get("record_ID") or ""),
                title=title or "Untitled",
                thumbnail=thumb,
                full_url=img,
                source="smithsonian",
                license="PD",
                license_url="https://creativecommons.org/publicdomain/mark/1.0/",
                type="image",
                author=", ".join(names) if names else "",
                source_url=desc.get("record_link") or "",
                dimensions=None,
            ))

        total = (data.get("response") or {}).get("rowCount", 0)
        return MediaSearchResponse(
            results=results,
            total=total,
            page=page,
            has_more=len(rows) == per_page,
        )

    def get(self, result_id: str) -> MediaResult | None:
        return None
