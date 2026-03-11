"""
Tiered Retrieval Manager - 3-tier fallback with cross-tier back-fill.

Resolution order:
    Tier 1  →  Azure AI Search (vector/semantic)
    Tier 2  →  Local disk cache (data/cache/*.json)
    Tier 3  →  BLS public API (direct fetch)

Each tier that returns data back-fills the tiers above it so the next
query hits a higher (cheaper / faster) tier.  Back-fills are fire-and-
forget — failures are logged but never raise to the caller.

    T1 hit  →  write cache files (T2) in background
    T2 hit  →  upsert to Azure Search (T1) in background
    T3 hit  →  T2 already written by fetcher; upsert to Azure Search (T1) in background
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import sys

# Handle imports for both module and script execution
try:
    from rag.data import vector_store_manager
    from rag.data.catalog_resolver import CatalogResolver
    from rag.data.data_fetcher import BlsDataSeriesFetcher
    from rag.data.indexes import BLSSeriesIndex, BLSSeriesMetadata
    from configs.CONSTANTS import BLS_SERIES_RELATIVE_PATH, BLS_SERIES_DATA_RELATIVE_PATH
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from rag.data import vector_store_manager
    from rag.data.catalog_resolver import CatalogResolver
    from rag.data.data_fetcher import BlsDataSeriesFetcher
    from rag.data.indexes import BLSSeriesIndex, BLSSeriesMetadata
    from configs.CONSTANTS import BLS_SERIES_RELATIVE_PATH, BLS_SERIES_DATA_RELATIVE_PATH

logger = logging.getLogger(__name__)

# Minimum number of data points that counts as a "hit" (not an empty result)
_MIN_DATA_POINTS = 1


class TieredRetrievalManager:
    """
    3-tier retrieval with automatic cross-tier back-fill.

    Drop-in replacement for RetrievalManager — returns the same
    ``{'metadata': [...], 'data': [...]}`` dict used by AugmentationManager.
    """

    def __init__(
        self,
        max_metadata_results: int = 8,
        max_data_results: int = 40,
        start_year: str = "2021",
        max_cache_age_days: int = 30,
    ):
        self.max_metadata_results = max_metadata_results
        self.max_data_results = max_data_results
        self.start_year = start_year
        self.max_cache_age_days = max_cache_age_days
        self.catalog = CatalogResolver(BLS_SERIES_RELATIVE_PATH)
        self.cache_dir = Path(BLS_SERIES_DATA_RELATIVE_PATH).resolve()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def retrieve(self, query: str) -> Dict[str, List[dict]]:
        """
        Retrieve BLS data using 3-tier fallback, back-filling each tier.

        Returns:
            {'metadata': [...], 'data': [...], 'tier_used': 1|2|3}
        """
        tier1_result = await self._try_tier1(query)
        if self._has_data(tier1_result):
            logger.info("[TieredRetrieval] Tier 1 (Azure Search) hit")
            asyncio.create_task(self._backfill_t1_to_t2(tier1_result))
            return {**tier1_result, "tier_used": 1}

        logger.info("[TieredRetrieval] Tier 1 miss — falling back to Tier 2 (cache)")
        series_ids = self.catalog.resolve(query, max_results=self.max_data_results)

        tier2_result = self._try_tier2(series_ids)
        if self._has_data(tier2_result):
            logger.info("[TieredRetrieval] Tier 2 (cache) hit for %d series", len(series_ids))
            asyncio.create_task(self._backfill_t2_to_t1(tier2_result, series_ids))
            return {**tier2_result, "tier_used": 2}

        logger.info("[TieredRetrieval] Tier 2 miss — falling back to Tier 3 (BLS API)")
        tier3_result = await self._try_tier3(series_ids, query)
        if self._has_data(tier3_result):
            logger.info("[TieredRetrieval] Tier 3 (BLS API) hit for %d series", len(series_ids))
            # Cache (T2) already written by BlsDataSeriesFetcher.fetch_all_series()
            asyncio.create_task(self._backfill_t3_to_t1(tier3_result, series_ids))
            return {**tier3_result, "tier_used": 3}

        logger.warning("[TieredRetrieval] All three tiers returned no data for query: %s", query)
        return {"metadata": [], "data": [], "tier_used": 0}

    # ------------------------------------------------------------------
    # Tier 1 — Azure AI Search
    # ------------------------------------------------------------------

    async def _try_tier1(self, query: str) -> Dict[str, List[dict]]:
        """Search Azure AI Search metadata + data indexes."""
        try:
            metadata_results = await vector_store_manager.search_metadata(
                query=query,
                top=self.max_metadata_results,
            )
            if not metadata_results:
                return {"metadata": [], "data": []}

            series_ids = [m.get("seriesId") for m in metadata_results if m.get("seriesId")]
            filter_expr = self._build_series_filter(series_ids) if series_ids else None

            data_results = await vector_store_manager.search_data(
                query=query,
                top=self.max_data_results,
                filter_expr=filter_expr,
            )
            return {"metadata": metadata_results, "data": data_results}
        except Exception as exc:
            logger.debug("[TieredRetrieval] Tier 1 error: %s", exc)
            return {"metadata": [], "data": []}

    # ------------------------------------------------------------------
    # Tier 2 — Disk cache
    # ------------------------------------------------------------------

    def _try_tier2(self, series_ids: List[str]) -> Dict[str, List[dict]]:
        """Read matching series files from local cache directory.
        
        Skips files that are stale (older than max_cache_age_days) so that
        the caller falls through to T3 for a fresh API fetch.
        """
        if not series_ids or not self.cache_dir.exists():
            return {"metadata": [], "data": []}

        metadata: List[dict] = []
        data: List[dict] = []

        for sid in series_ids:
            cache_file = self.cache_dir / f"{sid}.json"
            if not cache_file.exists():
                continue
            try:
                with open(cache_file) as f:
                    raw = json.load(f)

                # --- Staleness check -------------------------------------------
                # Prefer explicit last_fetched_utc stamp written by T3 fetches.
                # Fall back to file mtime for files written before this field existed.
                last_fetched_str = raw.get("last_fetched_utc")
                if last_fetched_str:
                    last_fetched = datetime.fromisoformat(last_fetched_str).replace(
                        tzinfo=timezone.utc
                    )
                else:
                    mtime = cache_file.stat().st_mtime
                    last_fetched = datetime.fromtimestamp(mtime, tz=timezone.utc)

                age_days = (datetime.now(timezone.utc) - last_fetched).days
                if age_days > self.max_cache_age_days:
                    logger.info(
                        "[TieredRetrieval] Cache stale (%d days) for %s — skipping T2",
                        age_days, sid,
                    )
                    continue
                # ----------------------------------------------------------------

                series_meta = self.catalog.get_series_metadata(sid)
                display_name = series_meta.get("name", sid)

                # Build metadata record
                metadata.append({
                    "seriesId": sid,
                    "name": display_name,
                    "level": series_meta.get("level", ""),
                    "state": series_meta.get("state", ""),
                    "county": series_meta.get("county", ""),
                })

                # Build data records (same shape as Azure Search results)
                for pt in raw.get("data", []):
                    if pt.get("period", "").startswith("M") and pt.get("period") != "M13":
                        data.append({
                            "seriesId": f"{sid}_{pt['year']}_{pt['period']}",
                            "seriesTitle": sid,
                            "displayName": display_name,
                            "value": pt.get("value", ""),
                            "year": pt.get("year", ""),
                            "period": pt.get("period", ""),
                            "periodName": pt.get("periodName", ""),
                            "footnotes": "",
                        })
            except Exception as exc:
                logger.debug("[TieredRetrieval] Cache read error for %s: %s", sid, exc)

        return {"metadata": metadata, "data": data}

    # ------------------------------------------------------------------
    # Tier 3 — BLS API
    # ------------------------------------------------------------------

    async def _try_tier3(
        self, series_ids: List[str], query: str
    ) -> Dict[str, List[dict]]:
        """Fetch directly from BLS API; fetcher also writes to cache.
        
        After a successful fetch, stamps each cache file with
        last_fetched_utc so subsequent _try_tier2 calls can correctly
        evaluate freshness without relying on filesystem mtime.
        """
        if not series_ids:
            return {"metadata": [], "data": []}
        try:
            fetcher = BlsDataSeriesFetcher()
            # fetch_all_series is synchronous — run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            records: List[BLSSeriesIndex] = await loop.run_in_executor(
                None,
                lambda: fetcher.fetch_all_series(
                    series_ids=series_ids, start_year=self.start_year
                ),
            )
            # Stamp cache files with fetch timestamp so staleness checks are accurate
            self._stamp_cache_files(series_ids)
            return self._records_to_retrieval_result(records, series_ids)
        except Exception as exc:
            logger.warning("[TieredRetrieval] Tier 3 (BLS API) error: %s", exc)
            return {"metadata": [], "data": []}

    def _stamp_cache_files(self, series_ids: List[str]) -> None:
        """Write last_fetched_utc into each cache file for the given series.
        
        Only called after a successful T3 (BLS API) fetch so the timestamp
        reflects actual data freshness, not a T1 backfill.
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        for sid in series_ids:
            cache_file = self.cache_dir / f"{sid}.json"
            if not cache_file.exists():
                continue
            try:
                with open(cache_file) as f:
                    raw = json.load(f)
                raw["last_fetched_utc"] = now_utc
                with open(cache_file, "w") as f:
                    json.dump(raw, f, indent=2)
            except Exception as exc:
                logger.debug("[TieredRetrieval] Failed to stamp %s: %s", sid, exc)

    # ------------------------------------------------------------------
    # Back-fill helpers (all fire-and-forget via create_task)
    # ------------------------------------------------------------------

    async def _backfill_t1_to_t2(self, tier1_result: Dict) -> None:
        """T1 hit → write/merge cache JSON files for each unique series."""
        try:
            # Group data points by their original series ID (seriesTitle field)
            groups: Dict[str, List[dict]] = {}
            for pt in tier1_result.get("data", []):
                sid = pt.get("seriesTitle") or pt.get("seriesId", "").rsplit("_", 2)[0]
                if sid:
                    groups.setdefault(sid, []).append(pt)

            self.cache_dir.mkdir(parents=True, exist_ok=True)
            for sid, points in groups.items():
                cache_file = self.cache_dir / f"{sid}.json"
                existing_data: List[dict] = []
                if cache_file.exists():
                    try:
                        with open(cache_file) as f:
                            existing_data = json.load(f).get("data", [])
                    except Exception:
                        pass

                # Merge: existing entries + new ones (deduplicate on year+period)
                existing_keys = {
                    (e["year"], e["period"]) for e in existing_data if "year" in e
                }
                for pt in points:
                    key = (pt.get("year", ""), pt.get("period", ""))
                    if key not in existing_keys:
                        existing_data.append({
                            "year": pt.get("year", ""),
                            "period": pt.get("period", ""),
                            "periodName": pt.get("periodName", ""),
                            "value": pt.get("value", ""),
                            "footnotes": [{"text": pt.get("footnotes", "")}] if pt.get("footnotes") else [{}],
                        })
                        existing_keys.add(key)

                with open(cache_file, "w") as f:
                    json.dump({"seriesID": sid, "data": existing_data}, f, indent=2)

            logger.info("[TieredRetrieval] T1→T2 back-fill: wrote %d cache files", len(groups))
        except Exception as exc:
            logger.warning("[TieredRetrieval] T1→T2 back-fill failed: %s", exc)

    async def _backfill_t2_to_t1(
        self, tier2_result: Dict, series_ids: List[str]
    ) -> None:
        """T2 hit → upsert into Azure Search (data + metadata indexes)."""
        try:
            # Data records
            data_records = [
                BLSSeriesIndex(
                    seriesId=pt["seriesId"],
                    seriesType=self.catalog.get_series_metadata(pt["seriesTitle"]).get("category", ""),
                    displayName=pt["displayName"],
                    timeStamp=f"{pt['year']}-{pt['period']}",
                    seriesTitle=pt["seriesTitle"],
                    value=pt["value"],
                    year=pt["year"],
                    period=pt["period"],
                    periodName=pt["periodName"],
                    footnotes=pt.get("footnotes", ""),
                )
                for pt in tier2_result.get("data", [])
            ]
            if data_records:
                await vector_store_manager.upsert_data_batch(data_records)

            # Metadata records
            meta_records = []
            for sid in series_ids:
                info = self.catalog.get_series_metadata(sid)
                meta_records.append(
                    BLSSeriesMetadata(
                        seriesId=sid,
                        name=info["name"],
                        description=info["name"],
                        category=info["category"],
                        level=info["level"],
                        fips=info["fips"],
                        state=info["state"],
                        county=info["county"],
                        seasonal_adjustment="",
                        measure_type=info["category"],
                        frequency="monthly",
                        searchable_text=info["searchable_text"],
                    )
                )
            if meta_records:
                await vector_store_manager.upsert_metadata_batch(meta_records)

            logger.info(
                "[TieredRetrieval] T2→T1 back-fill: %d data records, %d metadata records",
                len(data_records),
                len(meta_records),
            )
        except Exception as exc:
            logger.warning("[TieredRetrieval] T2→T1 back-fill failed: %s", exc)

    async def _backfill_t3_to_t1(
        self, tier3_result: Dict, series_ids: List[str]
    ) -> None:
        """T3 hit → upsert into Azure Search (cache was already written by fetcher)."""
        # Reuse the same logic as T2→T1 since the result dict has the same shape
        await self._backfill_t2_to_t1(tier3_result, series_ids)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _has_data(result: Optional[Dict]) -> bool:
        return bool(result and result.get("data"))

    @staticmethod
    def _build_series_filter(series_ids: List[str]) -> str:
        filters = [
            f"search.ismatch('{sid}', 'seriesId')" for sid in series_ids[:10]
        ]
        return " or ".join(filters)

    def _records_to_retrieval_result(
        self, records: List[BLSSeriesIndex], series_ids: List[str]
    ) -> Dict[str, List[dict]]:
        """Convert BLSSeriesIndex list → retrieval result dict."""
        data = [
            {
                "seriesId": r.seriesId,
                "seriesTitle": r.seriesTitle,
                "displayName": r.displayName,
                "value": r.value,
                "year": r.year,
                "period": r.period,
                "periodName": r.periodName,
                "footnotes": r.footnotes or "",
            }
            for r in records
        ]
        metadata = [
            {
                "seriesId": sid,
                **self.catalog.get_series_metadata(sid),
            }
            for sid in series_ids
        ]
        return {"metadata": metadata, "data": data}
