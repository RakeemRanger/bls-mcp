# RAG Quick Reference

## What Was Built

Complete RAG (Retrieval-Augmented Generation) pipeline for BLS data queries integrated with Semantic Kernel.

**Enhanced with predictive analysis capabilities** - can answer both factual and forward-looking questions.

## How It Works

When a user asks: **"What's the unemployment rate in California?"**

1. **Kernel** receives query
2. **LLM** decides to call `query_bls_data` tool
3. **Tool** executes RAG pipeline:
   - **Retrieval**: Searches Azure AI Search for relevant series and data
   - **Augmentation**: Formats retrieved data as context (sorted by date)
4. **Tool returns** context to kernel
5. **LLM** generates final answer using the context

### Predictive Queries (NEW)

The system now handles forward-looking questions:

**User**: "What will California unemployment be next month?"

1. RAG retrieves historical data (e.g., Jan: 4.2%, Dec: 4.3%, Nov: 4.5%)
2. Data sorted by date (most recent first) for trend visibility
3. Augmentation detects predictive keywords (predict, forecast, will, next, trend)
4. Provides special instructions for trend analysis
5. LLM analyzes trend and generates: "Based on the declining trend from 4.5% → 4.3% → 4.2%, California unemployment could drop to around 4.0-4.1% in March 2026. However, actual values depend on economic conditions and seasonal factors."

**Supported predictive queries**:
- "What will unemployment be next month?"
- "Based on the trend, will it increase or decrease?"  
- "Predict Texas employment for Q2 2026"
- "Is this a seasonal pattern?"
- "Will California unemployment continue falling?"

## Key Files

| File | Purpose |
|------|---------|
| `retrieval.py` | Two-stage search (metadata → data) |
| `aug.py` | Format context for LLM |
| `gen.py` | System prompts and guidelines |
| `rag.py` | Orchestrates R→A→G pipeline |
| `bls_data_tool.py` | Kernel function that uses RAG |
| `kernel.py` | Registers tool with kernel |
| `vector_store_manager.py` | Azure AI Search operations |

## Setup Commands

```bash
# 1. Install Azure AI Search SDK
pip install azure-search-documents>=11.4.0

# 2. Set credentials
export AZURE_SEARCH_ENDPOINT="https://your-service.search.windows.net"
export AZURE_SEARCH_API_KEY="your-admin-key"

# 3. Initialize data
python3 scripts/initialize_data.py --start-year 2020

# 4. Test
python3 test_rag.py
```

## Test Commands

```bash
# Test imports
cd /home/nodebrite/autoaiden/bls-mcp
python3 -c "
import sys
sys.path.insert(0, 'src')
from core.kernel import blsKernel
print('Kernel loaded successfully')
"

# Test RAG pipeline
python3 test_rag.py

# Test with kernel
cd src
python3 -c "
import asyncio
from core.kernel import blsKernel

async def test():
    kernel = blsKernel()
    response = await kernel.run('What is the unemployment rate in Texas?')
    print(response)

asyncio.run(test())
"

# Run function app
cd src
func start
```

## Architecture

```
User Query
    ↓
blsKernel (Semantic Kernel)
    ↓
LLM (Azure OpenAI)
    ↓
BlsDataQueryPlugin.query_bls_data()
    ↓
RagPipeline
    ├→ RetrievalManager → Azure AI Search
    ├→ AugmentationManager → Format context
    └→ Return to kernel
    ↓
LLM generates final response with context
```

## Code Flow

```python
# In kernel.py - tool is registered
self.kernel.add_plugin(BlsDataQueryPlugin(), plugin_name="BlsDataQuery")

# In bls_data_tool.py - tool implementation
@kernel_function(name="query_bls_data")
async def query_bls_data(self, query: str) -> str:
    pipeline = self._get_rag_pipeline()
    retrieval_results = await pipeline.retrieval.retrieve(query)
    context = pipeline.augmentation.augment(query, retrieval_results)
    return context  # Kernel feeds this to LLM

# In retrieval.py - two-stage search
async def retrieve(self, query: str):
    # Stage 1: Find relevant series
    metadata = await vector_store_manager.search_metadata(query)
    # Stage 2: Get actual data
    data = await vector_store_manager.search_data(query)
    return {'metadata': metadata, 'data': data}

# In aug.py - format context
def augment(self, query: str, results: dict) -> str:
    # Format retrieved data as readable context
    context = format_series_info(results['metadata'])
    context += format_data_points(results['data'])
    return f"Context: {context}\n\nUser Question: {query}"
```

## Documentation

- **ARCHITECTURE.md**: Complete system architecture
- **RAG_IMPLEMENTATION.md**: Detailed RAG documentation
- **RAG_COMPLETION.md**: What was built
- **SETUP_VECTOR_STORE.md**: Azure AI Search setup
- **test_rag.py**: Test suite with examples

## Design Notes

- No emojis in code (per requirement)
- LLM can use emojis in responses if appropriate
- Professional tone via system prompts
- Async throughout for performance
- Graceful error handling
- Type hints and docstrings

## Azure AI Search Indexes

- **bls-timeseries-data**: Individual BLS data points (year, period, value)
- **bls-series-metadata**: Series descriptions for discovery

## Status

All components implemented and tested. Ready for:
1. Azure AI Search configuration
2. Data initialization
3. Production deployment

## Common Issues

**Import error**: Make sure `sys.path` includes 'src'
**No Azure AI Search**: Set AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY
**No data found**: Run `scripts/initialize_data.py` first
**Tool not called**: Query must be about BLS employment/unemployment data
