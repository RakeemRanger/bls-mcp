from pathlib import Path
import os

# Get the base directory (configs folder)
_BASE_DIR = Path(__file__).parent

# BLS Series configuration
BLS_SERIES_RELATIVE_PATH = str(_BASE_DIR / 'bls_series.json')
BLS_API_ENDPOINT = 'https://api.bls.gov/publicAPI/v2/timeseries/data/'
# Optional: set BLS_API_KEY env var for registered key (500 req/day vs 25 unregistered)
# Register free at https://data.bls.gov/registrationEngine/

# Cache directory (relative to data folder)
BLS_SERIES_DATA_RELATIVE_PATH = str(_BASE_DIR.parent / 'rag' / 'data' / 'cache')

# RAG prompts 
RAG_PROMPTS_RELATIVE_PATH = str(_BASE_DIR.parent / 'rag' / 'prompts' / 'templates')