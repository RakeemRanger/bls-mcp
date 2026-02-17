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

    # ---- State & county tools (LAUS) ----

    @kernel_function(
        name="get_state_unemployment_data",
        description=(
            "Get unemployment data for a US state. Accepts state name (e.g. 'Ohio'), "
            "abbreviation ('OH'), or FIPS code ('39'). "
            "Measure codes: 03=unemployment rate (default), 04=unemployment level, "
            "05=employment level, 06=labor force level."
        ),
    )
    def get_state_data(
        self,
        state: Annotated[str, "State name, abbreviation, or FIPS code"],
        measure: Annotated[str, "LAUS measure code: 03=rate, 04=unemployment, 05=employment, 06=labor force"] = "03",
    ) -> str:
        data = self._client.get_state_data(state, measure=measure)
        if not data:
            return json.dumps({"error": f"No data found for state: {state}"})
        return json.dumps(data, indent=2)

    @kernel_function(
        name="get_county_unemployment_data",
        description=(
            "Get unemployment data for a US county by its 5-digit FIPS code. "
            "Example: '39049' for Franklin County, OH. County data is NOT seasonally adjusted. "
            "Measure codes: 03=unemployment rate (default), 04=unemployment level, "
            "05=employment level, 06=labor force level."
        ),
    )
    def get_county_data(
        self,
        county_fips: Annotated[str, "5-digit county FIPS code (e.g. '39049')"],
        county_name: Annotated[str, "Human-readable county name for display"] = "",
        measure: Annotated[str, "LAUS measure code: 03=rate, 04=unemployment, 05=employment, 06=labor force"] = "03",
    ) -> str:
        data = self._client.get_county_data(county_fips, county_name=county_name, measure=measure)
        if not data:
            return json.dumps({"error": f"No data found for county FIPS: {county_fips}"})
        return json.dumps(data, indent=2)

    @kernel_function(
        name="list_us_states",
        description="List all US states with their FIPS codes and abbreviations. Useful for looking up FIPS codes.",
    )
    def list_states(self) -> str:
        states = self._client.list_states()
        return json.dumps(states, indent=2)
