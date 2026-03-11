# RAG Pipeline Implementation

## Overview

Complete Retrieval-Augmented Generation (RAG) pipeline for BLS data queries using Azure AI Search.

## Architecture

```
User Query
    |
    v
Kernel (Semantic Kernel)
    |
    v
BlsDataQueryPlugin (kernel tool)
    |
    v
RAG Pipeline
    |
    +-- Retrieval Layer
    |   - Search metadata (find relevant series)
    |   - Search data (get actual values)
    |
    +-- Augmentation Layer
    |   - Format context
    |   - Combine with query
    |
    +-- [Context returned to Kernel]
    |
    v
Kernel LLM generates final response
```

## Components

### 1. Retrieval Layer (`retrieval.py`)

**Purpose**: Search Azure AI Search indexes to find relevant BLS data

**Two-stage retrieval**:
1. **Metadata search**: Identifies which BLS series are relevant
   - Input: "California unemployment rate"
   - Searches: `bls-series-metadata` index
   - Output: List of series IDs (e.g., LASST060000000003)

2. **Data search**: Gets actual data points for those series
   - Input: Series IDs from stage 1
   - Searches: `bls-timeseries-data` index  
   - Output: Actual values with dates

**Configuration**:
```python
retrieval = RetrievalManager(
    max_metadata_results=5,  # Up to 5 relevant series
    max_data_results=20      # Up to 20 data points
)
```

### 2. Augmentation Layer (`aug.py`)

**Purpose**: Format retrieved data as structured context for LLM

**Process**:
1. Takes retrieval results (metadata + data)
2. Formats into readable context:
   ```
   RELEVANT BLS SERIES:
   - Unemployment Rate - California [LASST060000000003]
   
   BLS DATA:
   - California Unemployment Rate: 4.2 (January 2026)
   - California Unemployment Rate: 4.3 (December 2025)
   ```
3. Combines with original query
4. Adds instructions for response formatting

**No external dependencies** - pure Python formatting

### 3. Generation Layer (`gen.py`)

**Purpose**: Generate responses (currently handled by Kernel's LLM)

**System prompt guidelines**:
- Clear, professional language
- Cite specific data points with dates
- Explain trends and context
- Acknowledge limitations when data is insufficient
- LLM can use emojis if it chooses

**Note**: In kernel tool mode, generation is handled by the main kernel LLM using the augmented context.

### 4. RAG Pipeline Orchestrator (`rag.py`)

**Purpose**: Coordinate all three layers

**Usage**:
```python
from core.rag.rag import RagPipeline

pipeline = RagPipeline()

# Simple processing
response = await pipeline.process("California unemployment rate")

# Detailed results (for debugging)
details = await pipeline.process_with_details("California unemployment rate")
# Returns: {'query', 'retrieval', 'augmented_prompt', 'response'}
```

### 5. Kernel Tool (`bls_data_tool.py`)

**Purpose**: Semantic Kernel plugin that makes RAG pipeline available as a tool

**How it works**:
1. Registered with kernel as `BlsDataQuery` plugin
2. LLM automatically calls it when user asks about BLS data
3. Tool retrieves and augments data
4. Returns context to kernel
5. Kernel's LLM generates final answer

**Function signature**:
```python
@kernel_function(
    name="query_bls_data",
    description="Search and retrieve Bureau of Labor Statistics employment and unemployment data"
)
async def query_bls_data(query: str) -> str:
    # Returns augmented context
```

## Data Flow

### Without RAG (old):
```
User: "What's the unemployment rate in California?"
  -> Kernel
  -> LLM (no context)
  -> Generic response or hallucination
```

### With RAG (new):
```
User: "What's the unemployment rate in California?"
  -> Kernel
  -> LLM decides to call query_bls_data tool
  -> Tool searches Azure AI Search
  -> Tool finds: California series, recent values
  -> Tool returns: "RELEVANT BLS SERIES: ..."
  -> Kernel feeds context to LLM
  -> LLM generates: "Based on BLS data, California's unemployment rate was 4.2% in January 2026..."
```

## Setup

### 1. Install Dependencies
```bash
pip install azure-search-documents>=11.4.0
```

### 2. Configure Azure AI Search
```bash
export AZURE_SEARCH_ENDPOINT="https://your-service.search.windows.net"
export AZURE_SEARCH_API_KEY="your-admin-key"
```

### 3. Initialize Data
```bash
python3 scripts/initialize_data.py --start-year 2020
```

This creates two indexes:
- `bls-timeseries-data`: Individual data points
- `bls-series-metadata`: Series descriptions for discovery

### 4. Test RAG Pipeline
```bash
python3 test_rag.py
```

Expected output:
```
TEST 1: RETRIEVAL LAYER
Query: California unemployment rate
Metadata results: 3 series found
Data results: 10 data points found
Retrieval test PASSED
...
```

## Integration with Kernel

The kernel automatically loads the BLS data query tool:

```python
# In kernel.py
def _setup_plugins(self) -> None:
    self.kernel.add_plugin(TimePlugin(), plugin_name="TimePlugin")
    self.kernel.add_plugin(BlsMcpInformationPlugin(), plugin_name="BlsMcpInfo")
    self.kernel.add_plugin(BlsDataQueryPlugin(), plugin_name="BlsDataQuery")
```

When you run the function app:
```python
kernel = blsKernel()
response = await kernel.run("What's the unemployment rate in Texas?")
```

The kernel's LLM will:
1. See the query is about BLS data
2. Call `query_bls_data` tool
3. Get context with actual data
4. Generate response using that context

## Testing

### Manual Test
```python
import asyncio
from core.rag.rag import RagPipeline

async def test():
    pipeline = RagPipeline()
    result = await pipeline.process("unemployment rate in Florida")
    print(result)

asyncio.run(test())
```

### Test with Kernel
```bash
cd src
python3 -c "
import asyncio
from core.kernel import blsKernel

async def test():
    kernel = blsKernel()
    response = await kernel.run('What is the current unemployment rate in California?')
    print(response)

asyncio.run(test())
"
```

### Full Test Suite
```bash
python3 test_rag.py
```

## Error Handling

All layers handle errors gracefully:

```python
# No Azure AI Search configured
Error querying BLS data: AZURE_SEARCH_ENDPOINT environment variable not set

# No data found
Note: No relevant BLS data was found for this query.

# Network issues
Error querying BLS data: [network error details]
```

## Performance

### Retrieval Speed
- Metadata search: ~50-200ms
- Data search: ~50-200ms
- Total retrieval: ~100-400ms

### Result Limits
- Metadata: 5 series (configurable)
- Data: 20 points (configurable)

### Index Sizes
- Free tier: 50MB, 10K documents
- Estimated usage: ~6K-8K data records + ~200 metadata records
- Fits comfortably in free tier

## File Structure

```
src/core/
├── rag/
│   ├── retrieval/
│   │   └── retrieval.py        # RetrievalManager
│   ├── augmented/
│   │   └── aug.py              # AugmentationManager
│   ├── generation/
│   │   └── gen.py              # GenerationManager
│   ├── rag.py                  # RagPipeline orchestrator
│   └── data/
│       └── vector_store_manager.py  # Azure AI Search operations
├── tools/
│   └── bls_data_tool.py        # Kernel tool plugin
└── kernel.py                   # Kernel integration

test_rag.py                     # Test suite
```

## Troubleshooting

### "No module named 'azure.search'"
```bash
pip install azure-search-documents>=11.4.0
```

### "AZURE_SEARCH_ENDPOINT not set"
```bash
export AZURE_SEARCH_ENDPOINT="https://your-service.search.windows.net"
export AZURE_SEARCH_API_KEY="your-admin-key"
```

### "Index not found"
```bash
# Initialize data first
python3 scripts/initialize_data.py
```

### No results from search
- Check data was indexed: Run initialization script
- Check query: Try simpler queries like "unemployment rate"
- Check Azure portal: Verify indexes exist and have documents

### Tool not being called
- Check function description in `bls_data_tool.py`
- Query must be about BLS employment/unemployment data
- Try explicit queries: "What's the BLS unemployment rate for X?"

## Next Steps

1. **Tune retrieval**: Adjust max_results based on performance
2. **Add filters**: Filter by date range, geography level
3. **Semantic search**: Add vector embeddings for better relevance
4. **Caching**: Cache common queries to reduce API calls
5. **Monitoring**: Add logging for retrieval quality metrics

## Notes

- Code written without emojis per requirements
- LLM responses can include emojis if appropriate
- Professional tone enforced via system prompts
- All components handle missing Azure AI Search gracefully
- Designed for semantic kernel function calling pattern
