import requests
import json
import sys
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import List

# Handle imports for both direct execution and module import
try:
    from utils.json_util import JsonUtility
    from configs.CONSTANTS import (
        BLS_SERIES_RELATIVE_PATH,
        BLS_API_ENDPOINT,
        BLS_SERIES_DATA_RELATIVE_PATH
    )
    from rag.data.indexes import BLSSeriesIndex, BLSSeriesMetadata
except ModuleNotFoundError:
    # Add parent directory to path for direct script execution
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from utils.json_util import JsonUtility
    from configs.CONSTANTS import (
        BLS_SERIES_RELATIVE_PATH,
        BLS_API_ENDPOINT,
        BLS_SERIES_DATA_RELATIVE_PATH
    )
    from rag.data.indexes import BLSSeriesIndex, BLSSeriesMetadata


class BlsDataSeriesFetcher:
    """
    Fetches BLS series data and parses into BLSSeriesIndex objects
    """
    def __init__(self):
        self.series_file = Path(BLS_SERIES_RELATIVE_PATH).resolve()
        self.json_util = JsonUtility(str(self.series_file))
        self.loaded_json = self.json_util.load()
    
    def _parse_series_to_records(self, series_data: dict) -> List[BLSSeriesIndex]:
        """
        Parse BLS series JSON into BLSSeriesIndex records.
        Each data point becomes a separate record.
        """
        records = []
        series_id = series_data.get('seriesID', '')
        
        # Get series metadata from config if available
        series_info = self._get_series_info(series_id)
        
        # Parse each data point
        for data_point in series_data.get('data', []):
            # Combine footnotes into single string
            footnotes_text = ', '.join([
                f['text'] for f in data_point.get('footnotes', []) if f.get('text')
            ])
            
            # Create unique key: seriesId + year + period
            unique_key = f"{series_id}_{data_point['year']}_{data_point['period']}"
            
            record = BLSSeriesIndex(
                seriesId=unique_key,  # Unique key for each data point
                seriesType=series_info.get('type', 'unknown'),
                displayName=series_info.get('name', series_id),
                timeStamp=f"{data_point['year']}-{data_point['period']}",
                seriesTitle=series_id,  # Original series ID
                value=data_point.get('value', ''),
                year=data_point['year'],
                period=data_point['period'],
                periodName=data_point.get('periodName', ''),
                footnotes=footnotes_text
            )
            records.append(record)
        
        return records
    
    def _get_series_info(self, series_id: str) -> dict:
        """
        Look up series metadata from loaded config.
        Returns series type and name if found.
        """
        # Search national series
        for category, series_dict in self.loaded_json.get('national', {}).items():
            for series_key, series_info in series_dict.items():
                if series_info.get('series_id') == series_id:
                    return {
                        'type': f"{category}_{series_key}",
                        'name': series_info.get('name', series_id)
                    }
        
        # Search state series
        for state_key, state_info in self.loaded_json.get('state', {}).items():
            if isinstance(state_info, dict):
                for field, sid in state_info.items():
                    if sid == series_id and 'series_id' in field:
                        return {
                            'type': field.replace('_series_id', ''),
                            'name': f"{state_info.get('name', state_key)} {field.replace('_series_id', '').replace('_', ' ').title()}"
                        }
        
        # Search county series
        for county_key, county_info in self.loaded_json.get('county', {}).items():
            if isinstance(county_info, dict):
                for field, sid in county_info.items():
                    if sid == series_id and 'series_id' in field:
                        return {
                            'type': field.replace('_series_id', ''),
                            'name': f"{county_info.get('name', county_key)} {field.replace('_series_id', '').replace('_', ' ').title()}"
                        }
        
        # Default if not found
        return {'type': 'unknown', 'name': series_id}
    
    def fetch_all_series(self,
                         series_ids: list = [],
                         start_year: str = '2011',
                         ) -> List[BLSSeriesIndex]:
        """
        Fetch BLS data, cache to disk, and return parsed BLSSeriesIndex objects.
        
        Args:
            series_ids: List of BLS series IDs to fetch
            start_year: Start year for data retrieval
            
        Returns:
            List of BLSSeriesIndex records ready for ingestion
        """
        self.series_list = []
        self.end_year = str(datetime.now().year)
        if len(series_ids) == 0:
            raise Exception('No BLS series to process')
        for id in series_ids:
            self.series_list.append(id)
        import os
        headers = {'Content-type': 'application/json'}
        payload = {"seriesid": self.series_list, "startyear": f"{start_year}", "endyear": f"{self.end_year}"}
        api_key = os.getenv('BLS_API_KEY', '').strip()
        if api_key:
            payload["registrationkey"] = api_key
        data = json.dumps(payload)
        try:
            p = requests.post(BLS_API_ENDPOINT, data=data, headers=headers)
            json_data = json.loads(p.text)
        except Exception as e:
            raise Exception(f'Issue requesting BLS Data: {e}')

        # Check API-level status before parsing
        status = json_data.get('status', '')
        if status != 'REQUEST_SUCCEEDED':
            messages = json_data.get('message', [])
            msg_str = ' | '.join(messages) if messages else '(no message)'
            raise Exception(f'BLS API error [{status}]: {msg_str}')

        # Process and save each series
        cache_dir = Path(BLS_SERIES_DATA_RELATIVE_PATH).resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)

        all_records = []
        for series in json_data.get('Results', {}).get('series', []):
            seriesId = str(series['seriesID'])
            series_file = cache_dir / f'{seriesId}.json'
            
            # Cache: Save series data as JSON (backup)
            with open(series_file, 'w') as f:
                json.dump(series, f, indent=2)
            
            # Parse: Convert to BLSSeriesIndex objects
            records = self._parse_series_to_records(series)
            all_records.extend(records)
            
            print(f"Saved {seriesId} with {len(series.get('data', []))} data points → {len(records)} records")
        
        print(f"\nTotal: {len(all_records)} records ready for ingestion")
        return all_records

    def build_metadata_records(self, series_ids: list) -> List["BLSSeriesMetadata"]:
        """
        Build BLSSeriesMetadata objects from bls_series.json config.
        One record per unique series ID.
        """
        records = []
        seen = set()

        # National series
        for category, series_dict in self.loaded_json.get('national', {}).items():
            for series_key, series_info in series_dict.items():
                sid = series_info.get('series_id', '')
                if sid not in series_ids or sid in seen:
                    continue
                seen.add(sid)
                name = series_info.get('name', sid)
                seasonal = series_info.get('seasonal_adjustment', '')
                measure = 'rate' if 'rate' in series_key else 'level'
                searchable = f"{name} {category} national {seasonal} {series_key}".strip()
                records.append(BLSSeriesMetadata(
                    seriesId=sid,
                    name=name,
                    description=name,
                    category=category,
                    level='national',
                    fips='',
                    state='',
                    county='',
                    seasonal_adjustment=seasonal,
                    measure_type=measure,
                    frequency='monthly',
                    searchable_text=searchable,
                ))

        # State series
        for state_key, state_info in self.loaded_json.get('state', {}).items():
            if not isinstance(state_info, dict):
                continue
            state_name = state_info.get('name', state_key)
            fips = state_info.get('fips', '')
            for field_key, sid in state_info.items():
                if not isinstance(sid, str) or 'series_id' not in field_key:
                    continue
                if sid not in series_ids or sid in seen:
                    continue
                seen.add(sid)
                measure_label = field_key.replace('_series_id', '').replace('_', ' ').title()
                category = field_key.replace('_series_id', '').split('_')[0]
                name = f"{state_name} {measure_label}"
                searchable = f"{name} state {state_name} {fips}".strip()
                records.append(BLSSeriesMetadata(
                    seriesId=sid,
                    name=name,
                    description=name,
                    category=category,
                    level='state',
                    fips=fips,
                    state=state_name,
                    county='',
                    seasonal_adjustment='',
                    measure_type=category,
                    frequency='monthly',
                    searchable_text=searchable,
                ))

        # County series
        for county_key, county_info in self.loaded_json.get('county', {}).items():
            if not isinstance(county_info, dict):
                continue
            county_name = county_info.get('name', county_key)
            fips = county_info.get('fips', '')
            state_name = county_info.get('state', '')
            state_fips = county_info.get('state_fips', '')
            for field_key, sid in county_info.items():
                if not isinstance(sid, str) or 'series_id' not in field_key:
                    continue
                if sid not in series_ids or sid in seen:
                    continue
                seen.add(sid)
                measure_label = field_key.replace('_series_id', '').replace('_', ' ').title()
                category = field_key.replace('_series_id', '').split('_')[0]
                name = f"{county_name} {measure_label}"
                searchable = (
                    f"{name} county {county_name} {state_name} "
                    f"fips={fips} state_fips={state_fips}"
                ).strip()
                records.append(BLSSeriesMetadata(
                    seriesId=sid,
                    name=name,
                    description=name,
                    category=category,
                    level='county',
                    fips=fips,
                    state=state_name,
                    county=county_name,
                    seasonal_adjustment='',
                    measure_type=category,
                    frequency='monthly',
                    searchable_text=searchable,
                ))

        return records


if __name__ == "__main__":
    # Test the fetcher with parsing
    print("Testing BLS Data Fetcher with parsing...")
    fetcher = BlsDataSeriesFetcher()
    
    # Fetch national unemployment rate
    test_series = ['LNS14000000']  # National unemployment rate
    print(f"Fetching series: {test_series}")
    
    records = fetcher.fetch_all_series(series_ids=test_series, start_year='2024')
    
    print(f"\nFetched and parsed {len(records)} records successfully!")
    print(f"Cache files saved to: {Path(BLS_SERIES_DATA_RELATIVE_PATH).resolve()}")
    
    # Show sample record
    if records:
        print(f"\nSample record:")
        sample = records[0]
        print(f"  Series ID: {sample.seriesId}")
        print(f"  Type: {sample.seriesType}")
        print(f"  Name: {sample.displayName}")
        print(f"  Value: {sample.value}")
        print(f"  Period: {sample.periodName} {sample.year}")