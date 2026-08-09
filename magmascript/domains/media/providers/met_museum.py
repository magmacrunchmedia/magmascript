"""Metropolitan Museum of Art public domain collection. No API key required."""

from __future__ import annotations

import httpx

from magmascript.domains.media.tools import (
    MediaProvider,
    MediaResult,
    MediaSearchResponse,
)

API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"
BATCH_SIZE = 6


class MetMuseumProvider:
    """Met Museum public domain search. Two-step: search IDs, then fetch objects."""

    @property
    def info(self) -> MediaProvider:
        return MediaProvider(
            key="met_museum",
            label="Met Museum",
            color="#f5c542",
            needs_key=False,
            types=["image"],
        )

    def _fetch_objects(self, ids: list[int]) -> list[MediaResult]:
        """Fetch object details in batches."""
        results = []
        with httpx.Client(timeout=15) as client:
            for i in range(0, len(ids), BATCH_SIZE):
                batch = ids[i : i + BATCH_SIZE]
                for oid in batch:
                    try:
                        resp = client.get(f"{API_BASE}/objects/{oid}")
                        if resp.status_code != 200:
                            continue
                        obj = resp.json()
                        if not obj.get("primaryImageSmall"):
                            continue
                        results.append(MediaResult(
                            id=str(obj.get("objectID", "")),
                            title=obj.get("title") or "Untitled",
                            thumbnail=obj.get("primaryImageSmall") or "",
                            full_url=obj.get("primaryImage") or "",
                            source="met_museum",
                            license="PD",
                            license_url="https://www.metmuseum.org/about-the-met/policies-and-documents/open-access",
                            type="image",
                            author=obj.get("artistDisplayName") or "",
                            source_url=obj.get("objectURL") or "",
                            dimensions=None,
                        ))
                    except Exception:
                        continue
        return results

    def search(
        self,
        query: str,
        *,
        page: int = 1,
        per_page: int = 24,
        media_type: str = "",
        orientation: str = "",
    ) -> MediaSearchResponse:
        resp = httpx.get(f"{API_BASE}/search", params={"q": query, "hasImages": "true"}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        all_ids = data.get("objectIDs") or []

        if not all_ids:
            return MediaSearchResponse(results=[], total=0, page=page, has_more=False)

        total = len(all_ids)
        start = (page - 1) * per_page
        slice_ids = all_ids[start : start + per_page]
        results = self._fetch_objects(slice_ids)

        return MediaSearchResponse(
            results=results,
            total=total,
            page=page,
            has_more=start + len(slice_ids) < total,
        )

    def get(self, result_id: str) -> MediaResult | None:
        try:
            resp = httpx.get(f"{API_BASE}/objects/{result_id}", timeout=15)
            if resp.status_code != 200:
                return None
            obj = resp.json()
            return MediaResult(
                id=str(obj.get("objectID", "")),
                title=obj.get("title") or "Untitled",
                thumbnail=obj.get("primaryImageSmall") or "",
                full_url=obj.get("primaryImage") or "",
                source="met_museum",
                license="PD",
                license_url="https://www.metmuseum.org/about-the-met/policies-and-documents/open-access",
                type="image",
                author=obj.get("artistDisplayName") or "",
                source_url=obj.get("objectURL") or "",
                dimensions=None,
            )
        except Exception:
            return None
