import azure.functions as func
import logging
import json
import asyncio
from datetime import datetime
from pathlib import Path

from core.kernel import blsKernel
from core.rag.data.data_fetcher import BlsDataSeriesFetcher
from core.utils.json_util import JsonUtility

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Lazy initialize kernel on first request
_kernel = None

def get_kernel() -> blsKernel:
    """Get or create kernel instance (singleton pattern)"""
    global _kernel
    if _kernel is None:
        _kernel = blsKernel()
    return _kernel

@app.mcp_tool_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    tool_name="rakeem_bls_mcp",
    description="""Rakeem Bureau of Labor Statistics MCP Server.
            Answer about ANY Public BLS datapoints,
            Easily integrate predictive analysis.""",
    toolProperties="[]",
)
async def mcp_trigger(context) -> str:
    """
    MCP Tool trigger for BLS queries
    
    Args:
        context: MCP tool context with input arguments
        
    Returns:
        AI response as string
    """
    try:
        # Parse MCP tool input
        # Context structure depends on MCP implementation
        # Common patterns: context.arguments, context.input, or direct dict
        
        if hasattr(context, 'arguments'):
            query = context.arguments.get('query')
        elif isinstance(context, dict):
            query = context.get('query')
        else:
            query = str(context)
        
        logging.info(f"MCP trigger received query: {query}")
        
        # Run query through kernel (lazy initialized)
        kernel = get_kernel()
        response = await kernel.run(query)
        
        return response
        
    except Exception as e:
        logging.error(f"Error in MCP trigger: {e}")
        return f"Error processing query: {str(e)}"

@app.timer_trigger(
    arg_name="timer",
    run_on_startup=True,
    schedule="0 0 16 * *"  # Run at midnight on 1st day of every month (cron: min hour day month dayOfWeek)
)
async def fetch_bls_data(timer: func.TimerRequest) -> None:
    """
    Fetches BLS data incrementally starting from last run year.
    First run: 2011-current_year
    Subsequent runs: last_run_year-current_year (incremental updates only)
    """
    logging.info("Starting BLS data fetch...")
    
    try:
        last_run_file_path = Path("core/configs/bls_data_last_run.json")
        current_year = datetime.now().year
        
        # Determine start year (incremental fetch from last run year)
        start_year = 2011  # Default for first run
        try:
            if last_run_file_path.exists():
                last_run_util = JsonUtility(str(last_run_file_path))
                last_run_data = last_run_util.load()
                start_year = last_run_data.get('last_run_year', 2011)
                logging.info(f"Resuming from last run year: {start_year}")
            else:
                logging.info("First run - fetching from 2011")
        except Exception as e:
            logging.warning(f"Could not load last run data, starting from 2011: {e}")
        
        # Get series IDs to fetch
        series_config_path = Path("core/configs/bls_series.json")
        series_util = JsonUtility(str(series_config_path))
        series_config = series_util.load()
        
        # Extract series IDs from config
        series_ids = []
        
        # National series
        for category, series_dict in series_config.get('national', {}).items():
            for series_key, series_info in series_dict.items():
                series_ids.append(series_info['series_id'])
        
        # State series (all states)
        for state_key, state_info in series_config.get('state', {}).items():
            if isinstance(state_info, dict) and 'unemployment_rate_series_id' in state_info:
                series_ids.append(state_info['unemployment_rate_series_id'])
                series_ids.append(state_info['employment_level_series_id'])
        
        logging.info(f"Fetching {len(series_ids)} series from {start_year}-{current_year}...")
        
        # Fetch data incrementally
        fetcher = BlsDataSeriesFetcher()
        results = fetcher.fetch_all_series(
            series_ids=series_ids, 
            start_year=str(start_year)
        )
        
        # TODO: Ingest into vector store
        # await data_manager.ingest(results)
        
        # Save current year as last run year for next incremental fetch
        last_run_data = {
            "last_run": datetime.now().isoformat(),
            "last_run_year": current_year,
            "series_count": len(series_ids),
            "years_fetched": f"{start_year}-{current_year}",
            "status": "success"
        }
        
        # Ensure directory exists
        last_run_file_path.parent.mkdir(parents=True, exist_ok=True)
        last_run_file_path.write_text(json.dumps(last_run_data, indent=2))
        
        logging.info(f"BLS data fetch completed successfully ({start_year}-{current_year})")
        
    except Exception as e:
        logging.error(f"Error fetching BLS data: {e}")
        # Update last run with error status (don't update last_run_year on error)
        error_data = {
            "last_run": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }
        try:
            last_run_file_path.parent.mkdir(parents=True, exist_ok=True)
            last_run_file_path.write_text(json.dumps(error_data, indent=2))
        except:
            logging.error("Failed to write error status to last_run file")