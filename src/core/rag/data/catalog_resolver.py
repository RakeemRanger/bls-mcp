"""
Catalog Resolver - Resolves natural language queries to BLS series IDs
by scanning bls_series.json without requiring a vector store.

Used as the series-ID resolution layer for tier 2 (cache) and
tier 3 (BLS API) fallbacks in the tiered retrieval pipeline.
"""

import json
import re
from typing import List, Dict, Tuple


class CatalogResolver:
    """
    Matches a natural language query to BLS series IDs via keyword scoring
    against the bls_series.json catalog.

    No embeddings or vector store required — pure text matching.
    """

    def __init__(self, series_path: str):
        with open(series_path) as f:
            self.catalog: dict = json.load(f)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def resolve(self, query: str, max_results: int = 10) -> List[str]:
        """
        Return up to *max_results* series IDs that best match *query*.

        Args:
            query: Natural language query (e.g. "Ohio county unemployment rate").
            max_results: Maximum number of series IDs to return.

        Returns:
            Ordered list of series IDs (best match first).
        """
        tokens = self._tokenize(query)
        scored: List[Tuple[int, str]] = []

        # National
        for category, series_dict in self.catalog.get("national", {}).items():
            for series_key, series_info in series_dict.items():
                sid = series_info.get("series_id", "")
                if not sid:
                    continue
                text = (
                    f"{series_info.get('name', '')} {category} national "
                    f"{series_key} {series_info.get('seasonal_adjustment', '')}"
                )
                score = self._score(tokens, text)
                if score > 0:
                    scored.append((score, sid))

        # State
        for state_key, state_info in self.catalog.get("state", {}).items():
            if not isinstance(state_info, dict):
                continue
            state_name = state_info.get("name", "")
            fips = state_info.get("fips", "")
            for field_key, sid in state_info.items():
                if not isinstance(sid, str) or "series_id" not in field_key:
                    continue
                measure = field_key.replace("_series_id", "").replace("_", " ")
                text = f"{state_name} state {measure} {fips}"
                score = self._score(tokens, text)
                if score > 0:
                    scored.append((score, sid))

        # County
        for county_key, county_info in self.catalog.get("county", {}).items():
            if not isinstance(county_info, dict):
                continue
            county_name = county_info.get("name", "")
            state_name = county_info.get("state", "")
            fips = county_info.get("fips", "")
            state_fips = county_info.get("state_fips", "")
            for field_key, sid in county_info.items():
                if not isinstance(sid, str) or "series_id" not in field_key:
                    continue
                measure = field_key.replace("_series_id", "").replace("_", " ")
                text = (
                    f"{county_name} county {state_name} {measure} "
                    f"fips {fips} {state_fips}"
                )
                score = self._score(tokens, text)
                if score > 0:
                    scored.append((score, sid))

        scored.sort(key=lambda x: x[0], reverse=True)
        # Deduplicate while preserving order
        seen: set = set()
        result: List[str] = []
        for _, sid in scored:
            if sid not in seen:
                seen.add(sid)
                result.append(sid)
            if len(result) >= max_results:
                break
        return result

    def get_series_metadata(self, series_id: str) -> Dict:
        """
        Return catalog metadata for a given series ID.
        Used when building metadata records for back-fill into Azure Search.
        """
        # National
        for category, series_dict in self.catalog.get("national", {}).items():
            for series_key, series_info in series_dict.items():
                if series_info.get("series_id") == series_id:
                    return {
                        "level": "national",
                        "name": series_info.get("name", series_id),
                        "category": category,
                        "state": "",
                        "county": "",
                        "fips": "",
                        "searchable_text": (
                            f"{series_info.get('name', '')} {category} national"
                        ),
                    }

        # State
        for state_key, state_info in self.catalog.get("state", {}).items():
            if not isinstance(state_info, dict):
                continue
            for field_key, sid in state_info.items():
                if sid == series_id and "series_id" in field_key:
                    name = (
                        f"{state_info.get('name', state_key)} "
                        f"{field_key.replace('_series_id', '').replace('_', ' ').title()}"
                    )
                    return {
                        "level": "state",
                        "name": name,
                        "category": field_key.replace("_series_id", "").split("_")[0],
                        "state": state_info.get("name", state_key),
                        "county": "",
                        "fips": state_info.get("fips", ""),
                        "searchable_text": f"{name} state {state_info.get('name', '')}",
                    }

        # County
        for county_key, county_info in self.catalog.get("county", {}).items():
            if not isinstance(county_info, dict):
                continue
            for field_key, sid in county_info.items():
                if sid == series_id and "series_id" in field_key:
                    name = (
                        f"{county_info.get('name', county_key)} "
                        f"{field_key.replace('_series_id', '').replace('_', ' ').title()}"
                    )
                    return {
                        "level": "county",
                        "name": name,
                        "category": field_key.replace("_series_id", "").split("_")[0],
                        "state": county_info.get("state", ""),
                        "county": county_info.get("name", county_key),
                        "fips": county_info.get("fips", ""),
                        "searchable_text": (
                            f"{name} county {county_info.get('state', '')} "
                            f"fips {county_info.get('fips', '')}"
                        ),
                    }

        return {
            "level": "unknown",
            "name": series_id,
            "category": "unknown",
            "state": "",
            "county": "",
            "fips": "",
            "searchable_text": series_id,
        }

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> set:
        return set(re.findall(r"\b\w+\b", text.lower()))

    @staticmethod
    def _score(tokens: set, text: str) -> int:
        text_tokens = set(re.findall(r"\b\w+\b", text.lower()))
        return len(tokens & text_tokens)
