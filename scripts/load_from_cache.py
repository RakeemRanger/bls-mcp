#!/usr/bin/env python3
"""
Load BLS data from cached JSON files into Azure AI Search.
Use this when you have already fetched and cached BLS data locally.

Usage:
    python scripts/load_from_cache.py
"""
import sys
import asyncio
import logging
import json
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.rag.data.indexes import BLSSeriesIndex
from core.rag.data import vector_store_manager
from core.utils.json_util import JsonUtility

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_cached_series_to_records(series_data: dict, series_config: dict) -> list:
    """
    Parse cached BLS series JSON into BLSSeriesIndex records.
    Each data point becomes a separate record.
    """
    records = []
    series_id = series_data.get('seriesID', '')
    
    # Get series metadata from config if available
    series_info = get_series_info(series_id, series_config)
    
    # Parse each data point
    for data_point in series_data.get('data', []):
        # Skip if no value
        if not data_point.get('value'):
            continue
            
        # Combine footnotes into single string
        footnotes_text = ', '.join([
            f.get('text', '') for f in data_point.get('footnotes', []) if f.get('text')
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


def get_series_info(series_id: str, series_config: dict) -> dict:
    """
    Look up series metadata from config.
    Returns series type and name if found.
    """
    # Search national series
    for category, series_dict in series_config.get('national', {}).items():
        for series_key, series_info in series_dict.items():
            if series_info.get('series_id') == series_id:
                return {
                    'type': f"{category}_{series_key}",
                    'name': series_info.get('name', series_id)
                }
    
    # Search state series
    for state_key, state_info in series_config.get('state', {}).items():
        if isinstance(state_info, dict):
            for field, sid in state_info.items():
                if sid == series_id and 'series_id' in field:
                    return {
                        'type': field.replace('_series_id', ''),
                        'name': f"{state_info.get('name', state_key)} {field.replace('_series_id', '').replace('_', ' ').title()}"
                    }
    
    # Search county series
    for county_key, county_info in series_config.get('county', {}).items():
        if isinstance(county_info, dict):
            for field, sid in county_info.items():
                if sid == series_id and 'series_id' in field:
                    return {
                        'type': field.replace('_series_id', ''),
                        'name': f"{county_info.get('name', county_key)} {field.replace('_series_id', '').replace('_', ' ').title()}"
                    }
    
    # Default if not found
    return {'type': 'unknown', 'name': series_id}


async def load_from_cache():
    """Load BLS data from cache directory into Azure AI Search"""
    logger.info("="*60)
    logger.info("LOADING DATA FROM CACHE")
    logger.info("="*60)
    
    # Load series config
    config_path = Path(__file__).parent.parent / 'src' / 'core' / 'configs' / 'bls_series.json'
    json_util = JsonUtility(str(config_path))
    series_config = json_util.load()
    
    # Find cache directory
    cache_dir = Path(__file__).parent.parent / 'src' / 'core' / 'rag' / 'data' / 'cache'
    
    if not cache_dir.exists():
        logger.error(f"Cache directory not found: {cache_dir}")
        raise Exception(f"Cache directory not found: {cache_dir}")
    
    # Get all cached JSON files
    cache_files = list(cache_dir.glob('*.json'))
    logger.info(f"Found {len(cache_files)} cached series files")
    
    if not cache_files:
        logger.warning("No cached data files found")
        return 0
    
    all_records = []
    files_processed = 0
    files_with_data = 0
    
    # Process each cached file
    for cache_file in cache_files:
        if cache_file.name == '__init__.py':
            continue
            
        try:
            with open(cache_file, 'r') as f:
                series_data = json.load(f)
            
            series_id = series_data.get('seriesID', '')
            data_points = series_data.get('data', [])
            
            files_processed += 1
            
            if not data_points:
                logger.debug(f"Skipping {series_id} (no data)")
                continue
            
            # Parse to records
            records = parse_cached_series_to_records(series_data, series_config)
            
            if records:
                all_records.extend(records)
                files_with_data += 1
                logger.info(f"Loaded {series_id}: {len(data_points)} data points → {len(records)} records")
            
        except Exception as e:
            logger.warning(f"Failed to process {cache_file.name}: {e}")
            continue
    
    logger.info(f"\nProcessed {files_processed} files, {files_with_data} with data")
    logger.info(f"Total records to upload: {len(all_records)}")
    
    if all_records:
        # Upload in batches (Azure Search has limits)
        batch_size = 1000
        logger.info(f"\nUploading in batches of {batch_size}...")
        
        for i in range(0, len(all_records), batch_size):
            batch = all_records[i:i+batch_size]
            logger.info(f"Uploading batch {i//batch_size + 1}/{(len(all_records)-1)//batch_size + 1} ({len(batch)} records)...")
            await vector_store_manager.upsert_data_batch(batch)
        
        logger.info(f"\n✓ Successfully loaded {len(all_records)} records from cache")
    
    return len(all_records)


def main():
    logger.info("="*60)
    logger.info("BLS MCP - LOAD FROM CACHE")
    logger.info("="*60)
    logger.info("")
    
    try:
        records_loaded = asyncio.run(load_from_cache())
        
        logger.info("="*60)
        logger.info("✓ CACHE LOAD COMPLETE!")
        logger.info("="*60)
        logger.info(f"Records loaded: {records_loaded}")
        logger.info("")
        logger.info("Your MCP endpoint is now ready with data!")
        logger.info("Try querying for BLS data through the MCP client.")
        
        return 0
        
    except Exception as e:
        logger.error("="*60)
        logger.error("✗ CACHE LOAD FAILED")
        logger.error("="*60)
        logger.error(str(e))
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
