import azure.functions as func
import logging
import json
import asyncio
from datetime import datetime
from pathlib import Path

from core.kernel import blsKernel
from core.rag.data.data_fetcher import BlsDataSeriesFetcher
from core.rag.data import vector_store_manager
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

@app.route(route="mcp", methods=["POST", "GET"], auth_level=func.AuthLevel.ANONYMOUS)
async def mcp_http_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    MCP Protocol HTTP endpoint (JSON-RPC 2.0 format)
    
    Implements Model Context Protocol over HTTP
    Supports JSON-RPC 2.0 requests
    """
    try:
        # Log raw request for debugging
        logging.info(f"MCP endpoint called - Method: {req.method}, Content-Type: {req.headers.get('Content-Type')}")
        
        # Handle GET requests (for SSE connection attempts)
        if req.method == 'GET':
            return func.HttpResponse(
                body=json.dumps({
                    "error": "This endpoint requires POST requests with JSON-RPC 2.0 format"
                }),
                mimetype="application/json",
                status_code=405
            )
        
        # Parse JSON-RPC request
        try:
            req_body = req.get_json()
        except Exception as json_err:
            # Log the raw body for debugging
            raw_body = req.get_body().decode('utf-8') if req.get_body() else ''
            logging.error(f"JSON parse error. Raw body: {raw_body[:500]}")
            raise ValueError(f"Invalid JSON: {str(json_err)}")
        
        # JSON-RPC 2.0 format validation
        jsonrpc = req_body.get('jsonrpc')
        method = req_body.get('method')
        params = req_body.get('params', {})
        request_id = req_body.get('id')
        
        logging.info(f"MCP request - jsonrpc: {jsonrpc}, method: {method}, id: {request_id}")
        
        # Handle MCP protocol methods
        if method == 'initialize':
            # MCP initialization handshake
            return func.HttpResponse(
                body=json.dumps({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {
                                "listChanged": False
                            }
                        },
                        "serverInfo": {
                            "name": "bls-mcp-server",
                            "version": "1.0.0"
                        }
                    }
                }),
                mimetype="application/json",
                status_code=200
            )
        
        elif method == 'tools/list':
            # List available tools
            return func.HttpResponse(
                body=json.dumps({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": [
                            {
                                "name": "query_bls_data",
                                "description": "Query Bureau of Labor Statistics data. Ask questions about employment, unemployment, inflation (CPI), wages, and other labor statistics.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "description": "Your question about BLS data"
                                        }
                                    },
                                    "required": ["query"]
                                }
                            }
                        ]
                    }
                }),
                mimetype="application/json",
                status_code=200
            )
        
        elif method == 'tools/call':
            # Execute tool call
            tool_name = params.get('name')
            tool_arguments = params.get('arguments', {})
            
            if tool_name == 'query_bls_data':
                query = tool_arguments.get('query')
                
                if not query:
                    return func.HttpResponse(
                        body=json.dumps({
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32602,
                                "message": "Invalid params: missing 'query' argument"
                            }
                        }),
                        mimetype="application/json",
                        status_code=200
                    )
                
                logging.info(f"Processing BLS query: {query}")
                
                try:
                    # Run query through kernel
                    kernel = get_kernel()
                    logging.info("Kernel initialized, running query...")
                    response = await kernel.run(query)
                    logging.info(f"Kernel response received, length: {len(str(response))}")
                    
                    result = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": str(response)
                                }
                            ]
                        }
                    }
                    
                    logging.info(f"Returning result for request_id: {request_id}")
                    
                    return func.HttpResponse(
                        body=json.dumps(result),
                        mimetype="application/json",
                        status_code=200
                    )
                    
                except Exception as kernel_error:
                    logging.error(f"Kernel execution error: {kernel_error}", exc_info=True)
                    return func.HttpResponse(
                        body=json.dumps({
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32603,
                                "message": f"Kernel error: {str(kernel_error)}"
                            }
                        }),
                        mimetype="application/json",
                        status_code=200
                    )
            else:
                return func.HttpResponse(
                    body=json.dumps({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Unknown tool: {tool_name}"
                        }
                    }),
                    mimetype="application/json",
                    status_code=200
                )
        
        else:
            # Method not found
            return func.HttpResponse(
                body=json.dumps({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }),
                mimetype="application/json",
                status_code=200
            )
        
    except ValueError as e:
        # JSON parsing error
        return func.HttpResponse(
            body=json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error: Invalid JSON"
                }
            }),
            mimetype="application/json",
            status_code=400
        )
    except Exception as e:
        logging.error(f"Error in MCP HTTP endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({
                "jsonrpc": "2.0",
                "id": request_id if 'request_id' in locals() else None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }),
            mimetype="application/json",
            status_code=500
        )

@app.timer_trigger(
    arg_name="timer",
    run_on_startup=True,  # Use scripts/initialize_data.py for initial load
    schedule="0 0 1 * *"  # Run at midnight on 1st day of every month
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

        # County series — incremental refresh of all indexed counties
        county_count = 0
        for county_key, county_info in series_config.get('county', {}).items():
            if not isinstance(county_info, dict):
                continue
            if not county_info.get('unemployment_rate_series_id'):
                continue
            series_ids.append(county_info['unemployment_rate_series_id'])
            series_ids.append(county_info['employment_level_series_id'])
            if 'labor_force_series_id' in county_info:
                series_ids.append(county_info['labor_force_series_id'])
            county_count += 1

        logging.info(f"Fetching {len(series_ids)} series ({county_count} counties) from {start_year}-{current_year}...")
        
        # Fetch data incrementally (returns parsed BLSSeriesIndex objects)
        fetcher = BlsDataSeriesFetcher()
        records = fetcher.fetch_all_series(
            series_ids=series_ids, 
            start_year=str(start_year)
        )
        
        logging.info(f"Parsed {len(records)} data records, upserting to Azure AI Search...")
        
        # Ensure indexes exist before upserting
        await vector_store_manager.create_all_indexes()
        
        # Ingest time series data
        await vector_store_manager.upsert_data_batch(records)
        
        # Build and ingest metadata (one record per series)
        metadata_records = fetcher.build_metadata_records(series_ids)
        await vector_store_manager.upsert_metadata_batch(metadata_records)
        
        logging.info(f"Successfully ingested {len(records)} records and {len(metadata_records)} metadata records to vector store")
        
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