# BLS MCP Initialization Scripts

## initialize_data.py

One-time initialization script to bulk load historical BLS data into the vector store.

### Usage

**Full initialization (metadata + data):**
```bash
python scripts/initialize_data.py
```

**Custom start year:**
```bash
python scripts/initialize_data.py --start-year 2015
```

**Metadata only:**
```bash
python scripts/initialize_data.py --metadata-only
```

**Series data only:**
```bash
python scripts/initialize_data.py --data-only
```

### Deployment Workflow

1. **Deploy infrastructure:**
   ```bash
   cd src/infra
   azd up
   ```

2. **Run initialization (one time):**
   ```bash
   python scripts/initialize_data.py
   ```
   
   This will:
   - Load all series metadata (descriptions, FIPS codes, patterns)
   - Fetch historical data from BLS API (2011-present)
   - Cache data locally
   - TODO: Ingest into vector store

3. **Deploy function app:**
   ```bash
   cd src
   func azure functionapp publish <YOUR_FUNCTION_APP_NAME>
   ```

4. **Automatic updates:**
   - Timer trigger runs monthly (1st of each month)
   - Fetches only new data incrementally
   - Keeps data fresh automatically

### What Gets Loaded

**Metadata (~150 records):**
- 50+ state series definitions
- 30+ county series definitions  
- National series definitions
- Series ID patterns

**Time Series Data (varies by year range):**
- National: ~10 series × 15 years × 12 months = ~1,800 records
- States: ~100 series × 15 years × 12 months = ~18,000 records
- Counties: ~60 series × 15 years × 12 months = ~10,800 records
- **Total: ~30,000+ data points**

### Rate Limits

BLS Public API limits:
- 25 series per query
- 500 queries per day

The script batches requests in chunks of 50 series to stay within limits.

### Monitoring

Check `src/core/configs/initialization_status.json` for:
- Initialization date
- Records loaded
- Year range
- Last update timestamp
