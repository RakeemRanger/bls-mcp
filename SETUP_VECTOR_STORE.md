# Vector Store Setup Guide

## Overview
The BLS MCP Server uses Azure AI Search as the vector store for:
1. **Time Series Data Index** (`bls-timeseries-data`): Individual BLS data points
2. **Metadata Index** (`bls-series-metadata`): Series discovery and query understanding

## Architecture

```
BLS API → data_fetcher.py → BLSSeriesIndex objects
                              ↓
                         vector_store_manager.py
                              ↓
                     Azure AI Search Indexes
                              ↓
                         retrieval.py → RAG
```

## Prerequisites

### 1. Install Azure AI Search SDK

```bash
cd /home/nodebrite/autoaiden/bls-mcp
source blsvenv/bin/activate
pip install azure-search-documents>=11.4.0
```

Or update from requirements.txt:
```bash
pip install -r src/requirements.txt
```

### 2. Create Azure AI Search Service

#### Option A: Using Azure Portal
1. Go to [Azure Portal](https://portal.azure.com)
2. Create new **Azure AI Search** resource
3. Choose **Free** tier (50MB, 10K documents - sufficient for pilot)
4. Note the **Endpoint** (e.g., `https://your-service.search.windows.net`)
5. Go to **Keys** → Copy **Primary admin key**

#### Option B: Using Azure CLI
```bash
# Set variables
RESOURCE_GROUP="bls-mcp-rg"
LOCATION="eastus"
SEARCH_SERVICE="bls-search-$(date +%s)"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Azure AI Search (free tier)
az search service create \
  --name $SEARCH_SERVICE \
  --resource-group $RESOURCE_GROUP \
  --sku free \
  --location $LOCATION

# Get endpoint and key
az search service show --name $SEARCH_SERVICE --resource-group $RESOURCE_GROUP --query "searchServiceUri" -o tsv
az search admin-key show --service-name $SEARCH_SERVICE --resource-group $RESOURCE_GROUP --query "primaryKey" -o tsv
```

### 3. Set Environment Variables

Add to your `.env` file or export:
```bash
export AZURE_SEARCH_ENDPOINT="https://your-service.search.windows.net"
export AZURE_SEARCH_API_KEY="your-admin-key-here"
```

For Azure Functions, add to `local.settings.json`:
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AZURE_SEARCH_ENDPOINT": "https://your-service.search.windows.net",
    "AZURE_SEARCH_API_KEY": "your-admin-key-here"
  }
}
```

## Testing the Setup

### Test 1: Verify Configuration
```bash
cd /home/nodebrite/autoaiden/bls-mcp
python3 src/core/rag/data/vector_store_manager.py
```

Expected output:
```
✓ Azure AI Search credentials are set
✓ Azure AI Search SDK is installed
```

### Test 2: Run Data Fetcher
```bash
python3 src/core/rag/data/data_fetcher.py
```

Should fetch BLS data and show:
```
✓ Fetched and parsed 25 records successfully!
```

### Test 3: Initialize Data (with Azure Search ready)
```bash
# Metadata only (quick test)
python3 scripts/initialize_data.py --metadata-only

# Full initialization (takes longer)
python3 scripts/initialize_data.py --start-year 2020
```

Expected output:
```
✓ Upserted N metadata records to bls-series-metadata index
✓ Upserted N data records to bls-timeseries-data index
```

## Index Schemas

### Time Series Data Index (`bls-timeseries-data`)
- **id**: Unique key (seriesId_year_period)
- **seriesId**: BLS series identifier
- **seriesType**: Category (e.g., "unemployment_rate")
- **displayName**: Human-readable name
- **year**: Year of data point
- **period**: Period code (M01-M12, etc.)
- **periodName**: Human-readable period
- **value**: Numeric value
- **footnotes**: Optional footnotes

### Metadata Index (`bls-series-metadata`)
- **id**: Series identifier (seriesId)
- **seriesId**: BLS series identifier
- **name**: Series name
- **category**: employment/unemployment
- **level**: national/state/county
- **state**: State name (if applicable)
- **fips**: FIPS code (if applicable)
- **county**: County name (if applicable)
- **description**: Full description
- **searchable_text**: Combined text for search

## Integration Points

### ✅ Completed
1. **data_fetcher.py**: Fetches from BLS API, returns `BLSSeriesIndex` objects
2. **vector_store_manager.py**: Handles upsert/search operations
3. **function_app.py**: Timer trigger integrated with vector store upsert
4. **initialize_data.py**: Bulk load script integrated with vector store

### ⏳ Pending
1. **retrieval.py**: Query metadata → find series → retrieve data
2. **aug.py**: Prepare context from retrieved records
3. **gen.py**: Generate response using LLM with context
4. **Index creation**: Indexes must be created before first upsert
   - Azure AI Search will auto-create on first upload
   - Or manually define schema for better control

## Data Flow

### Monthly Updates (Timer Trigger)
```
Timer Trigger → function_app.py
                     ↓
            Extract series IDs from config
                     ↓
            data_fetcher.fetch_all_series()
                     ↓
            Parsed BLSSeriesIndex objects
                     ↓
            vector_store_manager.upsert_data_batch()
                     ↓
            Azure AI Search index updated
```

### Initial Load (Scripts)
```
scripts/initialize_data.py
         ↓
Load metadata from bls_series.json
         ↓
metadata_loader.load_metadata_from_config()
         ↓
vector_store_manager.upsert_metadata_batch()
         ↓
Fetch all historical data (batched)
         ↓
data_fetcher.fetch_all_series() per batch
         ↓
vector_store_manager.upsert_data_batch() per batch
```

## Troubleshooting

### "No module named 'azure.search'"
```bash
pip install azure-search-documents>=11.4.0
```

### "AZURE_SEARCH_ENDPOINT environment variable not set"
Check your environment variables are loaded:
```bash
echo $AZURE_SEARCH_ENDPOINT
# Should output your endpoint URL
```

For Azure Functions, verify `local.settings.json` has the values.

### "Index not found" error
Azure AI Search will auto-create indexes on first upload. If you get this error:
1. Ensure credentials are correct
2. Check service tier supports custom indexes
3. Manually create index via Azure Portal or CLI

### Rate limit errors from BLS API
- BLS API limit: 500 requests/day, 25 series per request
- Use batching in initialize_data.py (already implemented)
- Cache files in `src/core/rag/data/cache/` prevent re-fetching

## Next Steps

1. **Install Dependencies**: `pip install azure-search-documents>=11.4.0`
2. **Create Azure AI Search**: Free tier is sufficient for testing
3. **Set Environment Variables**: Endpoint + API key
4. **Test Configuration**: Run vector_store_manager.py
5. **Initialize Data**: Run `scripts/initialize_data.py`
6. **Deploy Function App**: Azure Functions with timer trigger active

## Free Tier Limits

Azure AI Search Free Tier:
- **Storage**: 50 MB
- **Documents**: 10,000 documents
- **Indexes**: 3 indexes
- **API calls**: No stated limit

Estimated usage:
- Metadata records: ~200 (one per series)
- Data records: ~6,000-8,000 (assuming 2-3 years × 200 series × 12 months)
- **Fits comfortably in free tier!**

For production with >10 years history or >200 series:
- Upgrade to Basic tier (~$75/month)
- Or use alternative: ChromaDB (local), Qdrant (cloud/local)
