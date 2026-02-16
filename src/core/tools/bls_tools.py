import json
from typing import Annotated

from semantic_kernel.functions import kernel_function

from core.lib.bls_client import BLSClient


class BLSPlugin:
    """Semantic Kernel plugin for querying Bureau of Labor Statistics data."""

    def __init__(self):
        self._client = BLSClient()

    @kernel_function(
        name="get_bls_series_data",
        description="Get BLS time series data for a specific series ID (e.g. LNS14000000 for unemployment rate).",
    )
    def get_series_data(
        self,
        series_id: Annotated[str, "The BLS series ID to retrieve data for"],
    ) -> str:
        data = self._client.get_series(series_id)
        if not data:
            return json.dumps({"error": f"No data found for series ID: {series_id}"})
        return json.dumps(data, indent=2)

    @kernel_function(
        name="search_bls_series",
        description="Search for BLS series by keyword (e.g. 'unemployment', 'CPI', 'employment', 'wages').",
    )
    def search_series(
        self,
        keyword: Annotated[str, "Keyword to search for in BLS series names"],
    ) -> str:
        results = self._client.search_series(keyword)
        if not results:
            return json.dumps({"message": f"No series found matching '{keyword}'"})
        return json.dumps(results, indent=2)

    @kernel_function(
        name="list_available_bls_series",
        description="List all available BLS data series with their IDs and descriptions.",
    )
    def list_series(self) -> str:
        series = self._client.list_available_series()
        return json.dumps(series, indent=2)

    @kernel_function(
        name="get_all_bls_data",
        description="Get all cached BLS data across all series. Use for broad analysis across multiple indicators.",
    )
    def get_all_data(self) -> str:
        all_data = self._client.get_all_cached_data()
        summary = {}
        for series_id, records in all_data.items():
            if records:
                latest = records[0]
                summary[series_id] = {
                    "series_name": latest.get("series_name"),
                    "latest_value": latest.get("value"),
                    "latest_period": f"{latest.get('year', '')} {latest.get('period', '')}".strip(),
                    "total_records": len(records),
                }
        return json.dumps(summary, indent=2)
