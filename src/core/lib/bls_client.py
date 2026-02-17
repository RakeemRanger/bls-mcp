import os
import json
import logging
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

# v2 requires registration key; v1 is public but more limited
BLS_API_V1_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
BLS_API_V2_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# ---------------------------------------------------------------------------
# FIPS codes – used to build LAUS series IDs for state & county data
# ---------------------------------------------------------------------------
STATE_FIPS = {
    "Alabama": "01", "Alaska": "02", "Arizona": "04", "Arkansas": "05",
    "California": "06", "Colorado": "08", "Connecticut": "09", "Delaware": "10",
    "District of Columbia": "11", "Florida": "12", "Georgia": "13", "Hawaii": "15",
    "Idaho": "16", "Illinois": "17", "Indiana": "18", "Iowa": "19",
    "Kansas": "20", "Kentucky": "21", "Louisiana": "22", "Maine": "23",
    "Maryland": "24", "Massachusetts": "25", "Michigan": "26", "Minnesota": "27",
    "Mississippi": "28", "Missouri": "29", "Montana": "30", "Nebraska": "31",
    "Nevada": "32", "New Hampshire": "33", "New Jersey": "34", "New Mexico": "35",
    "New York": "36", "North Carolina": "37", "North Dakota": "38", "Ohio": "39",
    "Oklahoma": "40", "Oregon": "41", "Pennsylvania": "42", "Rhode Island": "44",
    "South Carolina": "45", "South Dakota": "46", "Tennessee": "47", "Texas": "48",
    "Utah": "49", "Vermont": "50", "Virginia": "51", "Washington": "53",
    "West Virginia": "54", "Wisconsin": "55", "Wyoming": "56",
    "Puerto Rico": "72",
}

# Reverse lookup: FIPS code → state name
FIPS_TO_STATE = {v: k for k, v in STATE_FIPS.items()}

# Common abbreviations → full name
STATE_ABBREVIATIONS = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming", "PR": "Puerto Rico",
}

# LAUS measure codes (last two digits of a LAUS series ID)
LAUS_MEASURES = {
    "03": "Unemployment Rate",
    "04": "Unemployment",
    "05": "Employment",
    "06": "Labor Force",
}

# Major BLS series IDs covering key *national* labor statistics
BLS_SERIES = {
    # Consumer Price Index (CPI)
    "CUUR0000SA0": "CPI - All Urban Consumers, All Items, US City Average",
    "SUUR0000SA0": "CPI - All Urban Wage Earners, All Items, US City Average",
    "CUUR0000SAF1": "CPI - Food",
    "CUUR0000SAH1": "CPI - Shelter",
    "CUUR0000SETA01": "CPI - New Vehicles",
    "CUUR0000SETB01": "CPI - Used Cars and Trucks",
    "CUUR0000SAM": "CPI - Medical Care",
    "CUUR0000SA0E": "CPI - Energy",
    # Employment / Unemployment
    "LNS14000000": "Unemployment Rate",
    "LNS12000000": "Employment Level",
    "LNS11000000": "Civilian Labor Force Level",
    "LNS13000000": "Unemployment Level",
    "LNS14000006": "Unemployment Rate - Black or African American",
    "LNS14000003": "Unemployment Rate - Hispanic or Latino",
    "LNS14000009": "Unemployment Rate - White",
    # Nonfarm Payrolls (Current Employment Statistics)
    "CES0000000001": "Total Nonfarm Employment",
    "CES0500000001": "Total Private Employment",
    "CES1000000001": "Mining and Logging Employment",
    "CES2000000001": "Construction Employment",
    "CES3000000001": "Manufacturing Employment",
    "CES4000000001": "Trade, Transportation, and Utilities Employment",
    "CES5000000001": "Information Employment",
    "CES5500000001": "Financial Activities Employment",
    "CES6000000001": "Professional and Business Services Employment",
    "CES6500000001": "Education and Health Services Employment",
    "CES7000000001": "Leisure and Hospitality Employment",
    "CES8000000001": "Other Services Employment",
    "CES9000000001": "Government Employment",
    # Average Hourly Earnings
    "CES0500000003": "Average Hourly Earnings - Total Private",
    # Job Openings and Labor Turnover (JOLTS)
    "JTS000000000000000JOL": "Total Nonfarm Job Openings",
    "JTS000000000000000HIL": "Total Nonfarm Hires",
    "JTS000000000000000TSL": "Total Nonfarm Separations",
    "JTS000000000000000QUL": "Total Nonfarm Quits",
    # Producer Price Index (PPI)
    "WPUFD4": "PPI - Finished Goods",
    "WPUFD49104": "PPI - Finished Consumer Foods",
    "WPUFD49116": "PPI - Finished Energy Goods",
}

class BLSClient:
    """
    Client for fetching and caching Bureau of Labor Statistics data.

    Fetches all major BLS series on first call and caches them in memory
    so subsequent requests don't hit the BLS API.
    """

    def __init__(self):
        api_key_raw = os.getenv("BLS_API_KEY", "")
        # Ignore placeholder values
        self._api_key: str | None = api_key_raw if api_key_raw and not api_key_raw.startswith("<") else None
        # v1 (no key): max 25 series, 10-year span. v2 (with key): max 50 series, 20-year span.
        self._max_batch_size = 50 if self._api_key else 25
        self._api_url = BLS_API_V2_URL if self._api_key else BLS_API_V1_URL
        self._cache: dict[str, list[dict]] = {}
        self._series_metadata: dict[str, str] = BLS_SERIES
        self._last_fetched: datetime | None = None
        self._cache_ttl = timedelta(hours=24)
        logger.info(f"BLS client initialized (registered={'yes' if self._api_key else 'no'}, batch_size={self._max_batch_size})")

    @property
    def is_cache_valid(self) -> bool:
        """Check if cached data is still fresh."""
        if not self._last_fetched or not self._cache:
            return False
        return datetime.now() - self._last_fetched < self._cache_ttl

    def _build_payload(self, series_ids: list[str], start_year: str, end_year: str) -> str:
        """Build the JSON payload for the BLS API."""
        payload = {
            "seriesid": series_ids,
            "startyear": start_year,
            "endyear": end_year,
        }
        if self._api_key:
            payload["registrationkey"] = self._api_key
        return json.dumps(payload)

    def _fetch_batch(self, series_ids: list[str], start_year: str, end_year: str) -> dict:
        """Fetch a batch of series from the BLS API."""
        headers = {"Content-type": "application/json"}
        data = self._build_payload(series_ids, start_year, end_year)
        logger.info(f"BLS API request: {len(series_ids)} series, {start_year}-{end_year}, url={self._api_url}")
        response = requests.post(self._api_url, data=data, headers=headers)
        response.raise_for_status()
        result = response.json()
        if result.get("status") != "REQUEST_SUCCEEDED":
            logger.warning(f"BLS API response: {result.get('status')} - {result.get('message', '')}")
        return result

    def fetch_all_series(self, start_year: str = None, end_year: str = None) -> None:
        """
        Fetch all configured BLS series and store in cache.

        Batches requests in groups of 50 (BLS API limit).
        """
        if self.is_cache_valid:
            logger.info("BLS data cache is still valid, skipping fetch.")
            return

        if not end_year:
            end_year = str(datetime.now().year - 1)
        if not start_year:
            start_year = str(int(end_year) - 2)

        all_series_ids = list(self._series_metadata.keys())
        logger.info(f"Fetching {len(all_series_ids)} BLS series from {start_year} to {end_year} (batch_size={self._max_batch_size}).")

        for i in range(0, len(all_series_ids), self._max_batch_size):
            batch = all_series_ids[i:i + self._max_batch_size]
            try:
                result = self._fetch_batch(batch, start_year, end_year)
                if result.get("status") != "REQUEST_SUCCEEDED":
                    logger.warning(f"BLS API returned status: {result.get('status')}")
                    continue

                for series in result.get("Results", {}).get("series", []):
                    series_id = series["seriesID"]
                    records = []
                    for item in series["data"]:
                        footnotes = ", ".join(
                            fn["text"] for fn in item.get("footnotes", []) if fn and "text" in fn
                        )
                        records.append({
                            "series_id": series_id,
                            "series_name": self._series_metadata.get(series_id, "Unknown"),
                            "year": item["year"],
                            "period": item["period"],
                            "value": item["value"],
                            "footnotes": footnotes,
                        })
                    self._cache[series_id] = records

            except requests.RequestException as e:
                logger.error(f"Error fetching BLS batch: {e}")

        self._last_fetched = datetime.now()
        logger.info(f"Cached {len(self._cache)} BLS series.")

    def get_series(self, series_id: str) -> list[dict]:
        """Get cached data for a specific series."""
        self.fetch_all_series()
        return self._cache.get(series_id, [])

    def get_all_cached_data(self) -> dict[str, list[dict]]:
        """Get all cached BLS data."""
        self.fetch_all_series()
        return self._cache

    def search_series(self, keyword: str) -> list[dict]:
        """Search series by keyword in the series name."""
        self.fetch_all_series()
        keyword_lower = keyword.lower()
        results = []
        for series_id, name in self._series_metadata.items():
            if keyword_lower in name.lower():
                latest = self._cache.get(series_id, [{}])[0] if series_id in self._cache else {}
                results.append({
                    "series_id": series_id,
                    "series_name": name,
                    "latest_value": latest.get("value"),
                    "latest_period": f"{latest.get('year', '')} {latest.get('period', '')}".strip(),
                })
        return results

    def list_available_series(self) -> list[dict]:
        """List all available BLS series with their descriptions."""
        return [
            {"series_id": sid, "series_name": name}
            for sid, name in self._series_metadata.items()
        ]

    # ------------------------------------------------------------------
    # State & county helpers (LAUS – Local Area Unemployment Statistics)
    # ------------------------------------------------------------------

    @staticmethod
    def resolve_state(name_or_abbrev: str) -> tuple[str, str] | None:
        """
        Resolve a state name, abbreviation, or FIPS code to (fips, full_name).

        Returns None if the input cannot be matched.
        """
        val = name_or_abbrev.strip()

        # Check by abbreviation (e.g. "OH")
        upper = val.upper()
        if upper in STATE_ABBREVIATIONS:
            full = STATE_ABBREVIATIONS[upper]
            return STATE_FIPS[full], full

        # Check by full name (case-insensitive)
        for state, fips in STATE_FIPS.items():
            if state.lower() == val.lower():
                return fips, state

        # Check by FIPS code directly (e.g. "39")
        if val.zfill(2) in FIPS_TO_STATE:
            fips = val.zfill(2)
            return fips, FIPS_TO_STATE[fips]

        return None

    @staticmethod
    def build_state_series_id(fips: str, measure: str = "03", seasonal: str = "S") -> str:
        """
        Build a LAUS state-level series ID.

        Format: LA + seasonal(1) + area_code(15) + measure(2) = 20 chars
        Area code for state: ST + 2-digit FIPS + 11 zeros

        :param fips: 2-digit state FIPS code
        :param measure: LAUS measure – 03=rate, 04=unemployment, 05=employment, 06=labor force
        :param seasonal: S = seasonally adjusted, U = not seasonally adjusted
        """
        return f"LA{seasonal}ST{fips}00000000000{measure}"

    @staticmethod
    def build_county_series_id(county_fips: str, measure: str = "03") -> str:
        """
        Build a LAUS county-level series ID.

        Format: LA + U(1) + area_code(15) + measure(2) = 20 chars
        Area code for county: CN + 5-digit FIPS + 8 zeros
        County data is only available NOT seasonally adjusted.

        :param county_fips: 5-digit county FIPS code (e.g. "39049" for Franklin County, OH)
        :param measure: LAUS measure – 03=rate, 04=unemployment, 05=employment, 06=labor force
        """
        return f"LAUCN{county_fips}00000000{measure}"

    def get_state_data(
        self,
        state: str,
        measure: str = "03",
        start_year: str | None = None,
        end_year: str | None = None,
    ) -> list[dict]:
        """
        Fetch LAUS data for a state.

        :param state: State name, abbreviation, or FIPS code
        :param measure: 03=rate, 04=unemployment, 05=employment, 06=labor force
        :returns: List of data records, or error dict
        """
        resolved = self.resolve_state(state)
        if not resolved:
            return [{"error": f"Unknown state: '{state}'. Use a state name, abbreviation, or FIPS code."}]
        fips, state_name = resolved
        series_id = self.build_state_series_id(fips, measure)
        measure_name = LAUS_MEASURES.get(measure, measure)

        # Check cache first
        if series_id in self._cache and self.is_cache_valid:
            logger.info(f"Cache hit for state series {series_id}")
            return self._cache[series_id]

        # Fetch on demand
        if not end_year:
            end_year = str(datetime.now().year - 1)
        if not start_year:
            start_year = str(int(end_year) - 2)

        try:
            result = self._fetch_batch([series_id], start_year, end_year)
            if result.get("status") != "REQUEST_SUCCEEDED":
                return [{"error": f"BLS API error: {result.get('message', 'unknown')}"}]

            records = []
            for series in result.get("Results", {}).get("series", []):
                for item in series["data"]:
                    footnotes = ", ".join(
                        fn["text"] for fn in item.get("footnotes", []) if fn and "text" in fn
                    )
                    records.append({
                        "series_id": series_id,
                        "series_name": f"{state_name} - {measure_name}",
                        "state": state_name,
                        "year": item["year"],
                        "period": item["period"],
                        "value": item["value"],
                        "footnotes": footnotes,
                    })
            self._cache[series_id] = records
            return records

        except requests.RequestException as e:
            logger.error(f"Error fetching state data: {e}")
            return [{"error": f"Request failed: {e}"}]

    def get_county_data(
        self,
        county_fips: str,
        county_name: str = "",
        measure: str = "03",
        start_year: str | None = None,
        end_year: str | None = None,
    ) -> list[dict]:
        """
        Fetch LAUS data for a county.

        :param county_fips: 5-digit county FIPS code (e.g. "39049")
        :param county_name: Optional human-friendly name for the county
        :param measure: 03=rate, 04=unemployment, 05=employment, 06=labor force
        """
        county_fips = county_fips.strip().zfill(5)
        series_id = self.build_county_series_id(county_fips, measure)
        measure_name = LAUS_MEASURES.get(measure, measure)
        label = county_name or f"County FIPS {county_fips}"

        if series_id in self._cache and self.is_cache_valid:
            logger.info(f"Cache hit for county series {series_id}")
            return self._cache[series_id]

        if not end_year:
            end_year = str(datetime.now().year - 1)
        if not start_year:
            start_year = str(int(end_year) - 2)

        try:
            result = self._fetch_batch([series_id], start_year, end_year)
            if result.get("status") != "REQUEST_SUCCEEDED":
                return [{"error": f"BLS API error: {result.get('message', 'unknown')}"}]

            records = []
            for series in result.get("Results", {}).get("series", []):
                for item in series["data"]:
                    footnotes = ", ".join(
                        fn["text"] for fn in item.get("footnotes", []) if fn and "text" in fn
                    )
                    records.append({
                        "series_id": series_id,
                        "series_name": f"{label} - {measure_name}",
                        "county": label,
                        "year": item["year"],
                        "period": item["period"],
                        "value": item["value"],
                        "footnotes": footnotes,
                    })
            self._cache[series_id] = records
            return records

        except requests.RequestException as e:
            logger.error(f"Error fetching county data: {e}")
            return [{"error": f"Request failed: {e}"}]

    def list_states(self) -> list[dict]:
        """List all available states with their FIPS codes and abbreviations."""
        abbrev_to_state = {v: k for k, v in STATE_ABBREVIATIONS.items()}
        return [
            {
                "state": name,
                "abbreviation": abbrev_to_state.get(name, ""),
                "fips": fips,
                "example_series_id": self.build_state_series_id(fips),
            }
            for name, fips in sorted(STATE_FIPS.items())
        ]
