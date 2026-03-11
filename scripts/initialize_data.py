#!/usr/bin/env python3
"""
One-time initialization script for BLS MCP Server.
Run this during deployment to bulk load historical data into vector store.

Usage:
    python scripts/initialize_data.py [--start-year 2011] [--metadata-only]
"""
import sys
import argparse
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.rag.data.data_fetcher import BlsDataSeriesFetcher
from core.rag.data.metadata_loader import load_metadata_from_config, load_patterns_from_config
from core.rag.data import vector_store_manager
from core.utils.json_util import JsonUtility

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# State name/abbrev → 2-digit FIPS (mirrors generate_county_series.py)
_STATE_NAME_TO_FIPS = {
    "alabama": "01", "al": "01", "alaska": "02", "ak": "02",
    "arizona": "04", "az": "04", "arkansas": "05", "ar": "05",
    "california": "06", "ca": "06", "colorado": "08", "co": "08",
    "connecticut": "09", "ct": "09", "delaware": "10", "de": "10",
    "district of columbia": "11", "dc": "11",
    "florida": "12", "fl": "12", "georgia": "13", "ga": "13",
    "hawaii": "15", "hi": "15", "idaho": "16", "id": "16",
    "illinois": "17", "il": "17", "indiana": "18", "in": "18",
    "iowa": "19", "ia": "19", "kansas": "20", "ks": "20",
    "kentucky": "21", "ky": "21", "louisiana": "22", "la": "22",
    "maine": "23", "me": "23", "maryland": "24", "md": "24",
    "massachusetts": "25", "ma": "25", "michigan": "26", "mi": "26",
    "minnesota": "27", "mn": "27", "mississippi": "28", "ms": "28",
    "missouri": "29", "mo": "29", "montana": "30", "mt": "30",
    "nebraska": "31", "ne": "31", "nevada": "32", "nv": "32",
    "new hampshire": "33", "nh": "33", "new jersey": "34", "nj": "34",
    "new mexico": "35", "nm": "35", "new york": "36", "ny": "36",
    "north carolina": "37", "nc": "37", "north dakota": "38", "nd": "38",
    "ohio": "39", "oh": "39", "oklahoma": "40", "ok": "40",
    "oregon": "41", "or": "41", "pennsylvania": "42", "pa": "42",
    "rhode island": "44", "ri": "44", "south carolina": "45", "sc": "45",
    "south dakota": "46", "sd": "46", "tennessee": "47", "tn": "47",
    "texas": "48", "tx": "48", "utah": "49", "ut": "49",
    "vermont": "50", "vt": "50", "virginia": "51", "va": "51",
    "washington": "53", "wa": "53", "west virginia": "54", "wv": "54",
    "wisconsin": "55", "wi": "55", "wyoming": "56", "wy": "56",
    "puerto rico": "72", "pr": "72",
}


def _resolve_state_fips(state_arg: str) -> str:
    """Return 2-digit FIPS or raise ValueError."""
    key = state_arg.strip().lower()
    # Direct FIPS pass-through
    if key.isdigit() and len(key) <= 2:
        key = key.zfill(2)
        if key in _STATE_NAME_TO_FIPS.values():
            return key
    fips = _STATE_NAME_TO_FIPS.get(key)
    if not fips:
        raise ValueError(
            f"Unknown state '{state_arg}'. "
            "Use full name, 2-letter abbreviation, or 2-digit FIPS."
        )
    return fips


def load_series_ids_from_config(state_fips: str = None, county_only: bool = False):
    """
    Extract series IDs from bls_series.json.

    Args:
        state_fips:  If set, only county series for this 2-digit state FIPS are included.
                     National and state-level series are still included unless county_only=True.
        county_only: If True, skip national and state-level series (county rows only).
    """
    series_config_path = Path(__file__).parent.parent / 'src' / 'core' / 'configs' / 'bls_series.json'
    series_util = JsonUtility(str(series_config_path))
    series_config = series_util.load()

    series_ids = []

    if not county_only:
        # National series
        logger.info("Loading national series IDs...")
        for category, series_dict in series_config.get('national', {}).items():
            for series_key, series_info in series_dict.items():
                series_ids.append(series_info['series_id'])

        # State series
        logger.info("Loading state series IDs...")
        for state_key, state_info in series_config.get('state', {}).items():
            if isinstance(state_info, dict) and 'unemployment_rate_series_id' in state_info:
                series_ids.append(state_info['unemployment_rate_series_id'])
                series_ids.append(state_info['employment_level_series_id'])
                if 'labor_force_series_id' in state_info:
                    series_ids.append(state_info['labor_force_series_id'])

    # County series — optionally filtered by state FIPS
    county_label = f" (state_fips={state_fips})" if state_fips else " (all states)"
    logger.info(f"Loading county series IDs{county_label}...")
    county_count = 0
    for county_key, county_info in series_config.get('county', {}).items():
        if not isinstance(county_info, dict):
            continue
        if not county_info.get('unemployment_rate_series_id'):
            continue
        # Apply state filter: county fips starts with state_fips
        if state_fips and not county_info.get('fips', '').startswith(state_fips):
            continue
        series_ids.append(county_info['unemployment_rate_series_id'])
        series_ids.append(county_info['employment_level_series_id'])
        if 'labor_force_series_id' in county_info:
            series_ids.append(county_info['labor_force_series_id'])
        county_count += 1

    logger.info(f"  {county_count} counties queued.")
    return series_ids


async def create_indexes():
    """Create Azure AI Search indexes if they don't exist"""
    logger.info("="*60)
    logger.info("CREATING INDEXES")
    logger.info("="*60)
    
    try:
        success = await vector_store_manager.create_all_indexes()
        if not success:
            raise Exception("Failed to create one or more indexes")
        logger.info("✓ Index creation complete")
        return True
        
    except Exception as e:
        logger.error(f"✗ Index creation failed: {e}")
        raise


async def initialize_metadata():
    """Load and index series metadata"""
    logger.info("="*60)
    logger.info("LOADING METADATA")
    logger.info("="*60)
    
    try:
        # Load metadata records
        metadata_records = load_metadata_from_config()
        logger.info(f"✓ Loaded {len(metadata_records)} metadata records")
        
        # Load patterns
        pattern_records = load_patterns_from_config()
        logger.info(f"✓ Loaded {len(pattern_records)} pattern records")
        
        # Ingest metadata into vector store
        logger.info("Upserting metadata to Azure AI Search...")
        await vector_store_manager.upsert_metadata_batch(metadata_records)
        
        # Note: Patterns might need separate index or can be combined with metadata
        # For now, treating patterns as part of metadata collection
        
        logger.info("✓ Metadata initialization complete")
        return len(metadata_records) + len(pattern_records)
        
    except Exception as e:
        logger.error(f"✗ Metadata initialization failed: {e}")
        raise


async def initialize_series_data(start_year='2011', state_fips: str = None, county_only: bool = False):
    """Fetch and index historical BLS series data"""
    logger.info("="*60)
    logger.info("LOADING SERIES DATA")
    logger.info("="*60)

    try:
        # Get series IDs — optionally filtered
        series_ids = load_series_ids_from_config(state_fips=state_fips, county_only=county_only)
        logger.info(f"Found {len(series_ids)} series to fetch")
        
        # BLS API has rate limits - batch in chunks of 50
        batch_size = 50
        all_records = []
        
        for i in range(0, len(series_ids), batch_size):
            batch = series_ids[i:i+batch_size]
            logger.info(f"Fetching batch {i//batch_size + 1}/{(len(series_ids)-1)//batch_size + 1} ({len(batch)} series)...")
            
            fetcher = BlsDataSeriesFetcher()
            # fetch_all_series now returns parsed BLSSeriesIndex objects
            records = fetcher.fetch_all_series(series_ids=batch, start_year=start_year)
            
            logger.info(f"Fetched and parsed {len(records)} data records")
            
            # Ingest batch into vector store immediately
            logger.info(f"  Upserting batch to Azure AI Search...")
            await vector_store_manager.upsert_data_batch(records)
            
            all_records.extend(records)
        
        logger.info(f"✓ Series data initialization complete ({len(all_records)} total records)")
        return len(all_records)
        
    except Exception as e:
        logger.error(f"✗ Series data initialization failed: {e}")
        raise


def save_initialization_status(metadata_count, series_count, start_year):
    """Save initialization metadata for tracking"""
    status_file = Path(__file__).parent.parent / 'src' / 'core' / 'configs' / 'initialization_status.json'
    
    status_data = {
        "initialized": True,
        "initialization_date": datetime.now().isoformat(),
        "start_year": start_year,
        "end_year": datetime.now().year,
        "metadata_records": metadata_count,
        "series_fetched": series_count,
        "last_update": datetime.now().isoformat()
    }
    
    status_file.write_text(__import__('json').dumps(status_data, indent=2))
    logger.info(f"✓ Saved initialization status to {status_file}")


def main():
    parser = argparse.ArgumentParser(description='Initialize BLS MCP data store')
    parser.add_argument('--start-year', type=str, default='2011',
                       help='Start year for historical data (default: 2011)')
    parser.add_argument('--metadata-only', action='store_true',
                       help='Only load metadata, skip series data')
    parser.add_argument('--data-only', action='store_true',
                       help='Only load series data, skip metadata')
    parser.add_argument(
        '--county-only', action='store_true',
        help='Only load county-level series (skip national and state-level series)'
    )
    parser.add_argument(
        '--state', default=None,
        help=(
            'Limit county series ingestion to one state '
            '(full name, 2-letter abbreviation, or 2-digit FIPS). '
            'National and state-level series are unaffected unless --county-only is also set.'
        )
    )
    args = parser.parse_args()

    # Resolve optional state filter
    state_fips: str | None = None
    if args.state:
        try:
            state_fips = _resolve_state_fips(args.state)
            logger.info(f"State filter: {args.state} → FIPS {state_fips}")
        except ValueError as e:
            logger.error(str(e))
            return 1
    
    logger.info("="*60)
    logger.info("BLS MCP SERVER - DATA INITIALIZATION")
    logger.info("="*60)
    logger.info(f"Start Year: {args.start_year}")
    logger.info(f"Current Year: {datetime.now().year}")
    logger.info("")
    
    try:
        metadata_count = 0
        series_count = 0
        
        # Create indexes first (async)
        asyncio.run(create_indexes())
        logger.info("")
        
        # Load metadata (async)
        if not args.data_only:
            metadata_count = asyncio.run(initialize_metadata())
            logger.info("")
        
        # Load series data (async)
        if not args.metadata_only:
            series_count = asyncio.run(
                initialize_series_data(
                    args.start_year,
                    state_fips=state_fips,
                    county_only=args.county_only,
                )
            )
            logger.info("")
        
        # Save status
        save_initialization_status(metadata_count, series_count, args.start_year)
        
        logger.info("="*60)
        logger.info("✓ INITIALIZATION COMPLETE!")
        logger.info("="*60)
        logger.info(f"Metadata records: {metadata_count}")
        logger.info(f"Series fetched: {series_count}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Deploy your function app")
        logger.info("  2. Timer trigger will handle monthly updates")
        logger.info("  3. Query endpoint is ready to use!")
        logger.info("")
        logger.info("Tip: to add / refresh county data for a single state:")
        logger.info("  python scripts/generate_county_series.py --state <state>")
        logger.info("  python scripts/initialize_data.py --state <state> --county-only")

        return 0

    except Exception as e:
        logger.error("="*60)
        logger.error("✗ INITIALIZATION FAILED")
        logger.error("="*60)
        logger.error(str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
