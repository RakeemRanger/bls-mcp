# BLS MCP Server - Complete Architecture

## System Overview

RAG-powered MCP server for querying Bureau of Labor Statistics employment and unemployment data using Azure Functions, Semantic Kernel, and Azure AI Search.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                        │
│               (MCP Client / HTTP Request)                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           v
┌─────────────────────────────────────────────────────────────┐
│                    AZURE FUNCTIONS                           │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │              function_app.py                       │    │
│  │  - MCP Tool Trigger: mcp_trigger()                 │    │
│  │  - Timer Trigger: fetch_bls_data() [monthly]       │    │
│  └────────────┬───────────────────────────────────────┘    │
│               │                                             │
│               v                                             │
│  ┌────────────────────┐                                    │
│  │   blsKernel        │                                    │
│  │  (Semantic Kernel) │                                    │
│  │  Plugins:          │                                    │
│  │  - TimePlugin      │                                    │
│  │  - BlsMcpInfo      │                                    │
│  │  - BlsDataQuery    │                                    │
│  └────────┬───────────┘                                    │
└───────────┼─────────────────────────────────────────────────┘
            │
            v
┌─────────────────────────────────────────────────────────────┐
│                  TIERED RAG PIPELINE                         │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  1. BlsDataQueryPlugin (Kernel Tool)               │    │
│  │     - Triggered by LLM for BLS queries             │    │
│  └────────────┬───────────────────────────────────────┘    │
│               │                                             │
│               v                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │  2. TieredRetrievalManager                          │    │
│  │                                                     │    │
│  │  T1: Azure AI Search (vector/keyword)               │    │
│  │      hit → back-fill T2 cache (background)          │    │
│  │       ↓ miss                                        │    │
│  │  T2: Disk Cache (data/cache/*.json)                 │    │
│  │      staleness check (max_cache_age_days=30)        │    │
│  │      hit → back-fill T1 Azure Search (background)  │    │
│  │       ↓ miss / stale                                │    │
│  │  T3: BLS Public API (live fetch)                    │    │
│  │      writes T2 cache + stamps last_fetched_utc      │    │
│  │      back-fills T1 Azure Search (background)        │    │
│  └────────────┬───────────────────────────────────────┘    │
│               │                                             │
│               v                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │  3. AugmentationManager                             │    │
│  │     - Format retrieved data as context              │    │
│  │     - Append DATA SOURCE TIER to context            │    │
│  └────────────┬───────────────────────────────────────┘    │
└───────────────┼─────────────────────────────────────────────┘
                │
                v
┌─────────────────────────────────────────────────────────────┐
│               KERNEL LLM (Azure OpenAI)                      │
│          Generates final response with context              │
└─────────────────────────────────────────────────────────────┘

  Data stores (separate from query path):
  ┌───────────────────┐     ┌────────────────────┐
  │  T2: Disk Cache   │◄────│  T1: Azure Search  │
  │  data/cache/*.json│────►│  bls-timeseries    │
  │  source of truth  │     │  bls-metadata      │
  └───────────────────┘     └────────────────────┘
       ▲ write / stamp            ▲ upsert
       └──────────── T3: BLS API ─┘
```

## Data Flow

### Query Processing Flow

```
1. User Query
   "What's the unemployment rate in California?"
   
2. Function App receives request
   function_app.py -> mcp_trigger()
   
3. Kernel processes query
   blsKernel.run(query)
   
4. LLM analyzes query
   Determines BLS data needed
   
5. LLM calls kernel tool
   BlsDataQueryPlugin.query_bls_data("unemployment rate in California")
   
   6. Tiered RAG Retrieval
   TieredRetrievalManager.retrieve() — 3-tier fallback:
   
   T1 (Azure AI Search):  search metadata → search data
       hit  → return data, back-fill T2 cache (async)
       miss ↓
   T2 (Disk Cache):       CatalogResolver resolves series IDs
                          reads data/cache/{seriesId}.json
                          staleness check: last_fetched_utc > 30 days → miss
       hit  → return data, back-fill T1 Azure Search (async)
       miss / stale ↓
   T3 (BLS Public API):   fetch live data
                          BlsDataSeriesFetcher → writes cache + stamps last_fetched_utc
                          back-fills T1 Azure Search (async)
   
7. RAG Augmentation Stage
   AugmentationManager.augment()
   Formats context:
   "RELEVANT BLS SERIES:
    - Unemployment Rate - California [LASST060000000003]
    BLS DATA:
    - California Unemployment Rate: 4.2 (January 2026)
    - California Unemployment Rate: 4.3 (December 2025)"
   
8. Tool returns context to Kernel
   
9. Kernel feeds context to LLM
   
10. LLM generates final response
    "Based on BLS data, California's unemployment rate was 
     4.2% in January 2026, down from 4.3% in December 2025..."
```

### Data Ingestion Flow

```
1. Timer Trigger (Monthly)
   fetch_bls_data() runs on 1st of each month
   
2. Load Series Configuration
   Read bls_series.json
   Extract all series IDs (national, state, county)
   
3. Fetch Incremental Data
   BlsDataSeriesFetcher.fetch_all_series()
   ├─> Batch series IDs (25 per request)
   ├─> Call BLS API for each batch
   ├─> Cache JSON responses locally
   └─> Parse to BLSSeriesIndex objects
   
4. Upsert to Vector Store
   vector_store_manager.upsert_data_batch()
   Upload to Azure AI Search index
   
5. Update Tracking
   Save last_run_year for next incremental fetch
```

### Initial Data Load Flow

```
1. Run Initialization Script
   python3 scripts/initialize_data.py --start-year 2020
   
2. Load Metadata
   metadata_loader.load_metadata_from_config()
   ├─> Parse bls_series.json
   ├─> Create BLSSeriesMetadata records
   └─> Upsert to metadata index
   
3. Load Historical Data
   For each batch of 50 series:
   ├─> BlsDataSeriesFetcher.fetch_all_series()
   ├─> Cache JSON files
   ├─> Parse to BLSSeriesIndex objects
   └─> Upsert batch to data index
   
4. Save Status
   Write initialization_status.json
   Track completion and metrics
```

### Component Responsibilities

### Data Layer
- **data_fetcher.py**: BLS API integration, caching (`data/cache/*.json`), parsing
- **vector_store_manager.py**: Azure AI Search upsert + search operations
- **catalog_resolver.py**: Keyword-scores NL queries against `bls_series.json` to resolve series IDs (no vector DB required)
- **indexes/**: Data models with `@vectorstoremodel` decorators

### RAG Layer
- **tiered_retrieval.py**: 3-tier fallback (T1 Azure Search → T2 disk cache → T3 BLS API) with cross-tier back-fill and staleness control
- **retrieval.py**: Original single-tier Azure Search retrieval (kept for reference)
- **aug.py**: Context formatting, appends `DATA SOURCE TIER` annotation
- **gen.py**: Response generation (currently unused, handled by kernel)
- **rag.py**: Pipeline orchestration — wires `TieredRetrievalManager`

### Kernel Layer
- **kernel.py**: Semantic Kernel setup, plugin registration
- **tools/bls_data_tool.py**: RAG-powered kernel function
- **tools/info.py**: Information/help plugin

### Configuration Layer
- **config_loader.py**: Azure resource configuration
- **CONSTANTS.py**: Path constants
- **bls_series.json**: Complete series catalog (source for `CatalogResolver` in T2/T3)

### Orchestration Layer
- **function_app.py**: Azure Functions triggers
- **scripts/initialize_data.py**: One-time full data load (T3 → T2 → T1)
- **scripts/load_from_cache.py**: Rebuild T1 from T2 (`load_from_cache.py`)

## Tiered Retrieval — Data Store Roles

| Tier | Store | Role | Rebuilt by |
|------|-------|------|------------|
| T1 | Azure AI Search | Fast keyword index, derived | `load_from_cache.py` or back-fill |
| T2 | `data/cache/*.json` | **Source of truth**, durable | T3 fetch + `last_fetched_utc` stamp |
| T3 | BLS Public API | Upstream, always current | N/A (external) |

**T2 is the durable store.** T1 is always rebuildable from T2 with:
```bash
python scripts/load_from_cache.py
```

### Cache Freshness
Each cache file written by a T3 fetch is stamped with `last_fetched_utc`. `_try_tier2` skips files older than `max_cache_age_days` (default 30), causing a T3 re-fetch and restamping — keeping both T2 and T1 fresh automatically.

### Back-fill Loop

```
T1 hit  → write/merge T2 cache files (background task)
T2 hit  → upsert data + metadata to T1 Azure Search (background task)
T3 hit  → T2 already written by fetcher, stamp last_fetched_utc
           → upsert to T1 Azure Search (background task)
```

Back-fills are fire-and-forget (`asyncio.create_task`) — failures are logged but never block the response.

## Technology Stack

### Core Framework
- **Python 3.12**: Runtime
- **Azure Functions**: Serverless hosting
- **Semantic Kernel**: LLM orchestration and tool calling

### AI/ML
- **Azure OpenAI**: LLM for generation
- **Azure AI Search**: Vector store (keyword + future semantic search)

### Data Sources
- **BLS Public API v2**: Employment/unemployment data
- **Local cache**: JSON backup files

### Authentication
- **DefaultAzureCredential**: Azure AD authentication
- **API Keys**: BLS API (optional), Azure AI Search

## Configuration Files

### Environment Variables
```bash
# Azure AI Inference (for LLM)
AZURE_AI_INFERENCE_ENDPOINT="https://your-foundry.inference.ai.azure.com"

# Azure AI Search (for RAG)
AZURE_SEARCH_ENDPOINT="https://your-service.search.windows.net"
AZURE_SEARCH_API_KEY="your-admin-key"

# Optional
BLS_API_KEY="your-bls-key"  # For higher rate limits
ENVIRONMENT="dev"           # or "prod"
```

### Function App Configuration
```json
// local.settings.json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AZURE_SEARCH_ENDPOINT": "...",
    "AZURE_SEARCH_API_KEY": "..."
  }
}
```

### Infrastructure Configuration
```json
// src/core/configs/dev-config.json
{
  "resourceGroupId": "/subscriptions/.../resourceGroups/...",
  "services": {
    "openai": {
      "resourceName": "your-foundry",
      "deploymentName": "gpt-4o"
    }
  }
}
```

## API Endpoints

### MCP Tool Trigger
```
POST /api/mcp_trigger
Content-Type: application/json

{
  "query": "What's the unemployment rate in California?"
}
```

### Timer Trigger
```
Automatic: Runs at 00:00 on 1st day of each month
Cron: "0 0 1 * *"
```

## Deployment

### Local Development
```bash
# Setup
cd bls-mcp
python3 -m venv blsvenv
source blsvenv/bin/activate
pip install -r src/requirements.txt

# Configure
export AZURE_SEARCH_ENDPOINT="..."
export AZURE_SEARCH_API_KEY="..."

# Initialize data
python3 scripts/initialize_data.py --start-year 2020

# Run function app
cd src
func start
```

### Azure Deployment
```bash
# Deploy infrastructure (Bicep)
az deployment group create \
  --resource-group bls-mcp-rg \
  --template-file src/infra/main.bicep

# Deploy function app
cd src
func azure functionapp publish your-function-app

# Configure app settings
az functionapp config appsettings set \
  --name your-function-app \
  --resource-group bls-mcp-rg \
  --settings \
    AZURE_SEARCH_ENDPOINT="..." \
    AZURE_SEARCH_API_KEY="..."
```

## Testing

### Unit Tests
```bash
# Test vector store manager
python3 src/core/rag/data/vector_store_manager.py

# Test data fetcher
python3 src/core/rag/data/data_fetcher.py
```

### Integration Tests
```bash
# Test RAG pipeline
python3 test_rag.py
```

### End-to-End Test
```bash
# Test kernel with RAG
cd src
python3 -c "
import asyncio
from core.kernel import blsKernel

async def test():
    kernel = blsKernel()
    response = await kernel.run('What is California unemployment rate?')
    print(response)

asyncio.run(test())
"
```

## Monitoring

### Logs
- Function App logs: Azure Portal -> Function App -> Log Stream
- Local logs: Terminal output when running `func start`

### Metrics to Track
- BLS API calls per day (limit: 500)
- Azure AI Search queries
- Average response time
- Cache hit rate
- Vector store size

### Error Scenarios
- BLS API rate limit: T2 cache absorbs load; T1 back-fill skipped gracefully
- Azure AI Search down: T2 cache serves queries; T3 used for cache misses
- Stale cache (>30 days): T2 falls through to T3 for fresh fetch + re-stamp
- All tiers fail: Graceful empty-result message returned to caller
- Missing credentials: Clear error with setup instructions

## Security

### Secrets Management
- Local: Environment variables or `.env` file
- Azure: Key Vault or Function App settings
- Never commit: configs.json (in .gitignore)

### Authentication
- Azure OpenAI: Managed Identity (DefaultAzureCredential)
- Azure AI Search: API key (admin key for indexing)
- BLS API: Optional API key for higher limits

## Performance

### Response Times
- BLS API fetch: 1-3 seconds per batch
- Azure AI Search: 100-400ms
- LLM generation: 1-3 seconds
- Total query: 2-7 seconds

### Optimization Strategies
- Cache BLS responses locally
- Batch Azure AI Search operations
- Limit retrieval result counts
- Use incremental updates (not full reloads)

## Scalability

### Current Capacity
- Azure AI Search Free: 50MB, 10K docs
- Estimated usage: ~8K docs
- BLS API: 500 calls/day

### Scaling Options
- Azure AI Search Basic: 2GB, 15 million docs
- BLS registered key: Higher rate limits
- Azure Functions: Auto-scales with load

## Future Enhancements

### Short Term
- Add semantic search (vector embeddings)
- Implement query caching
- Add date range filters
- Support time series comparisons

### Long Term
- Predictive analytics
- Trend visualization
- Multi-region data
- Real-time alerts on data changes

## Documentation

- [SETUP_VECTOR_STORE.md](SETUP_VECTOR_STORE.md): Azure AI Search setup
- [RAG_IMPLEMENTATION.md](RAG_IMPLEMENTATION.md): RAG pipeline details
- [scripts/README.md](scripts/README.md): Initialization guide
- [README.md](README.md): Project overview

## Support

For issues or questions:
1. Check documentation files
2. Review error messages (designed to be helpful)
3. Run test suite: `python3 test_rag.py`
4. Check Azure portal for service health
