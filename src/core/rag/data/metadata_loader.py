"""
Utility to load BLS series metadata from JSON config into vector store.
"""
import json
from pathlib import Path
from typing import List

from data.indexes import BLSSeriesMetadata, BLSSeriesPattern


def load_metadata_from_config(config_path: str = None) -> List[BLSSeriesMetadata]:
    """
    Parse bls_series.json and create BLSSeriesMetadata records for indexing.
    
    Args:
        config_path: Path to bls_series.json. If None, uses default location.
        
    Returns:
        List of BLSSeriesMetadata objects ready for ingestion.
    """
    if config_path is None:
        # Default to configs folder
        config_path = Path(__file__).parent.parent.parent / "configs" / "bls_series.json"
    
    with open(config_path, 'r') as f:
        data = json.load(f)
    
    metadata_records = []
    
    # Parse national series
    for category, series_dict in data.get('national', {}).items():
        for series_key, series_info in series_dict.items():
            record = BLSSeriesMetadata(
                seriesId=series_info['series_id'],
                name=series_info['name'],
                description=f"National {category} - {series_info['name']}",
                category=category,
                level="national",
                seasonal_adjustment=series_info.get('seasonal_adjustment', ''),
                measure_type=series_key,
                searchable_text=f"{series_info['name']} {category} national united states"
            )
            metadata_records.append(record)
    
    # Parse state series
    for state_key, state_info in data.get('state', {}).items():
        if state_key in ['unemployment', 'employment', 'pattern', 'note']:
            continue
            
        state_name = state_info['name']
        fips = state_info['fips']
        
        # Unemployment rate
        if 'unemployment_rate_series_id' in state_info:
            record = BLSSeriesMetadata(
                seriesId=state_info['unemployment_rate_series_id'],
                name=f"{state_name} Unemployment Rate",
                description=f"State-level unemployment rate for {state_name}",
                category="unemployment",
                level="state",
                fips=fips,
                state=state_name,
                measure_type="rate",
                searchable_text=f"{state_name} unemployment rate state {state_key}"
            )
            metadata_records.append(record)
        
        # Employment level
        if 'employment_level_series_id' in state_info:
            record = BLSSeriesMetadata(
                seriesId=state_info['employment_level_series_id'],
                name=f"{state_name} Employment Level",
                description=f"State-level employment level for {state_name}",
                category="employment",
                level="state",
                fips=fips,
                state=state_name,
                measure_type="level",
                searchable_text=f"{state_name} employment level state jobs {state_key}"
            )
            metadata_records.append(record)
        
        # Labor force
        if 'labor_force_series_id' in state_info:
            record = BLSSeriesMetadata(
                seriesId=state_info['labor_force_series_id'],
                name=f"{state_name} Labor Force",
                description=f"State-level labor force for {state_name}",
                category="employment",
                level="state",
                fips=fips,
                state=state_name,
                measure_type="labor_force",
                searchable_text=f"{state_name} labor force state workforce {state_key}"
            )
            metadata_records.append(record)
    
    # Parse county series
    for county_key, county_info in data.get('county', {}).items():
        if county_key in ['unemployment', 'employment', 'pattern', 'note']:
            continue
            
        county_name = county_info['name']
        state_name = county_info['state']
        fips = county_info['fips']
        
        # Unemployment rate
        if 'unemployment_rate_series_id' in county_info:
            record = BLSSeriesMetadata(
                seriesId=county_info['unemployment_rate_series_id'],
                name=f"{county_name}, {state_name} Unemployment Rate",
                description=f"County-level unemployment rate for {county_name}, {state_name}",
                category="unemployment",
                level="county",
                fips=fips,
                state=state_name,
                county=county_name,
                measure_type="rate",
                searchable_text=f"{county_name} {state_name} county unemployment rate {county_key}"
            )
            metadata_records.append(record)
        
        # Employment level
        if 'employment_level_series_id' in county_info:
            record = BLSSeriesMetadata(
                seriesId=county_info['employment_level_series_id'],
                name=f"{county_name}, {state_name} Employment Level",
                description=f"County-level employment level for {county_name}, {state_name}",
                category="employment",
                level="county",
                fips=fips,
                state=state_name,
                county=county_name,
                measure_type="level",
                searchable_text=f"{county_name} {state_name} county employment level jobs {county_key}"
            )
            metadata_records.append(record)
    
    return metadata_records


def load_patterns_from_config(config_path: str = None) -> List[BLSSeriesPattern]:
    """
    Extract series ID patterns from config for dynamic series construction.
    
    Returns:
        List of BLSSeriesPattern objects.
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "configs" / "bls_series.json"
    
    with open(config_path, 'r') as f:
        data = json.load(f)
    
    patterns = []
    
    # State patterns
    if 'patterns' in data.get('series_codes', {}):
        state_pattern = data['series_codes']['patterns'].get('state', {})
        patterns.append(BLSSeriesPattern(
            patternId="state_pattern",
            category="all",
            level="state",
            pattern=state_pattern.get('format', ''),
            description=state_pattern.get('example', ''),
            example=state_pattern.get('example', '')
        ))
        
        county_pattern = data['series_codes']['patterns'].get('county', {})
        patterns.append(BLSSeriesPattern(
            patternId="county_pattern",
            category="all",
            level="county",
            pattern=county_pattern.get('format', ''),
            description=county_pattern.get('example', ''),
            example=county_pattern.get('example', '')
        ))
    
    return patterns


if __name__ == "__main__":
    # Test the loader
    records = load_metadata_from_config()
    print(f"Loaded {len(records)} metadata records")
    print(f"\nExample record:")
    print(f"  Series ID: {records[0].seriesId}")
    print(f"  Name: {records[0].name}")
    print(f"  Category: {records[0].category}")
    print(f"  Level: {records[0].level}")
