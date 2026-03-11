"""
Vector Store Manager for BLS Data
Handles Azure AI Search operations for time series data and metadata indexes.

Note: Requires azure-search-documents package to be installed.
      Install with: pip install azure-search-documents>=11.4.0
"""

import os
from typing import List, Optional

try:
    from rag.data.indexes import BLSSeriesIndex, BLSSeriesMetadata
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from rag.data.indexes import BLSSeriesIndex, BLSSeriesMetadata


# Index names
DATA_INDEX_NAME = "bls-timeseries-data"
METADATA_INDEX_NAME = "bls-series-metadata"


def _validate_credentials() -> str:
    """Validate that Azure AI Search endpoint is set and return it."""
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    if not endpoint:
        raise ValueError(
            "AZURE_SEARCH_ENDPOINT environment variable not set. "
            "Set it to your Azure AI Search endpoint (e.g., https://myservice.search.windows.net)"
        )
    return endpoint


def _import_azure_search():
    """Import Azure AI Search client with helpful error message."""
    try:
        from azure.search.documents.aio import SearchClient
        from azure.identity.aio import DefaultAzureCredential
        return SearchClient, DefaultAzureCredential
    except ImportError as e:
        raise ImportError(
            "Azure AI Search SDK not found. Install it with:\n"
            "  pip install azure-search-documents>=11.4.0\n"
            "  pip install azure-identity\n"
            f"Original error: {e}"
        )


def _import_azure_search_admin():
    """Import Azure AI Search admin client for index management."""
    try:
        from azure.search.documents.indexes.aio import SearchIndexClient
        from azure.search.documents.indexes.models import (
            SearchIndex,
            SearchField,
            SearchFieldDataType,
            SimpleField,
            SearchableField
        )
        from azure.identity.aio import DefaultAzureCredential
        return SearchIndexClient, SearchIndex, SearchField, SearchFieldDataType, SimpleField, SearchableField, DefaultAzureCredential
    except ImportError as e:
        raise ImportError(
            "Azure AI Search SDK not found. Install it with:\n"
            "  pip install azure-search-documents>=11.4.0\n"
            "  pip install azure-identity\n"
            f"Original error: {e}"
        )


async def create_data_index() -> bool:
    """
    Create the BLS time series data index if it doesn't exist.
    
    Returns:
        True if index was created or already exists, False on error
    """
    endpoint = _validate_credentials()
    SearchIndexClient, SearchIndex, SearchField, SearchFieldDataType, SimpleField, SearchableField, DefaultAzureCredential = _import_azure_search_admin()
    
    try:
        async with DefaultAzureCredential() as credential:
            async with SearchIndexClient(
                endpoint=endpoint,
                credential=credential
            ) as client:
                # Check if index exists
                try:
                    existing_index = await client.get_index(DATA_INDEX_NAME)
                    print(f"✓ Index '{DATA_INDEX_NAME}' already exists")
                    return True
                except:
                    pass  # Index doesn't exist, create it
                
                # Define index schema based on BLSSeriesIndex model
                fields = [
                    SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                    SearchableField(name="seriesId", type=SearchFieldDataType.String, filterable=True, sortable=True),
                    SearchableField(name="seriesType", type=SearchFieldDataType.String, filterable=True),
                    SearchableField(name="displayName", type=SearchFieldDataType.String, filterable=True),
                    SimpleField(name="year", type=SearchFieldDataType.String, filterable=True, sortable=True),
                    SimpleField(name="period", type=SearchFieldDataType.String),
                    SimpleField(name="periodName", type=SearchFieldDataType.String),
                    SimpleField(name="value", type=SearchFieldDataType.String),
                    SearchableField(name="footnotes", type=SearchFieldDataType.String)
                ]
                
                index = SearchIndex(name=DATA_INDEX_NAME, fields=fields)
                await client.create_index(index)
                print(f"✓ Created index '{DATA_INDEX_NAME}'")
                return True
            
    except Exception as e:
        print(f"✗ Failed to create index '{DATA_INDEX_NAME}': {e}")
        return False


async def create_metadata_index() -> bool:
    """
    Create the BLS series metadata index if it doesn't exist.
    
    Returns:
        True if index was created or already exists, False on error
    """
    endpoint = _validate_credentials()
    SearchIndexClient, SearchIndex, SearchField, SearchFieldDataType, SimpleField, SearchableField, DefaultAzureCredential = _import_azure_search_admin()
    
    try:
        async with DefaultAzureCredential() as credential:
            async with SearchIndexClient(
                endpoint=endpoint,
                credential=credential
            ) as client:
                # Check if index exists
                try:
                    existing_index = await client.get_index(METADATA_INDEX_NAME)
                    print(f"✓ Index '{METADATA_INDEX_NAME}' already exists")
                    return True
                except:
                    pass  # Index doesn't exist, create it
                
                # Define index schema based on BLSSeriesMetadata model
                fields = [
                    SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                    SearchableField(name="seriesId", type=SearchFieldDataType.String, filterable=True),
                    SearchableField(name="name", type=SearchFieldDataType.String, filterable=True),
                    SearchableField(name="category", type=SearchFieldDataType.String, filterable=True),
                    SearchableField(name="level", type=SearchFieldDataType.String, filterable=True),
                    SearchableField(name="state", type=SearchFieldDataType.String, filterable=True),
                    SimpleField(name="fips", type=SearchFieldDataType.String),
                    SimpleField(name="county", type=SearchFieldDataType.String),
                    SearchableField(name="description", type=SearchFieldDataType.String),
                    SearchableField(name="searchable_text", type=SearchFieldDataType.String)
                ]
                
                index = SearchIndex(name=METADATA_INDEX_NAME, fields=fields)
                await client.create_index(index)
                print(f"✓ Created index '{METADATA_INDEX_NAME}'")
                return True
            
    except Exception as e:
        print(f"✗ Failed to create index '{METADATA_INDEX_NAME}': {e}")
        return False


async def create_all_indexes() -> bool:
    """
    Create all required indexes for BLS MCP.
    
    Returns:
        True if all indexes were created or already exist, False if any failed
    """
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "(not set)")
    print("Creating Azure AI Search indexes...")
    print(f"  Endpoint: {endpoint}")
    print()
    
    data_ok = await create_data_index()
    metadata_ok = await create_metadata_index()
    
    print()
    if data_ok and metadata_ok:
        print("✓ All indexes ready")
        return True
    else:
        print("✗ Some indexes failed to create")
        return False


async def upsert_data_batch(records: List[BLSSeriesIndex]) -> None:
    """
    Upsert a batch of BLS time series records to Azure AI Search.
    
    Implementation Note:
    This uses direct Azure AI Search SDK rather than Semantic Kernel's
    abstraction layer for better control over indexing operations.
    
    Args:
        records: List of BLSSeriesIndex objects to upsert
        
    Raises:
        ValueError: If Azure AI Search credentials are not set
        ImportError: If azure-search-documents package is not installed
    """
    if not records:
        print("No data records to upsert")
        return
    
    endpoint = _validate_credentials()
    SearchClient, DefaultAzureCredential = _import_azure_search()
    
    # Convert BLSSeriesIndex objects to dicts for Azure Search
    documents = []
    for record in records:
        doc = {
            "id": record.seriesId,  # Use seriesId as the key
            "seriesId": record.seriesId,
            "seriesType": record.seriesType,
            "displayName": record.displayName,
            "year": record.year,
            "period": record.period,
            "periodName": record.periodName,
            "value": record.value,
            "footnotes": record.footnotes or ""
        }
        documents.append(doc)
    
    # Upload to Azure AI Search using Managed Identity
    async with DefaultAzureCredential() as credential:
        async with SearchClient(
            endpoint=endpoint,
            index_name=DATA_INDEX_NAME,
            credential=credential
        ) as client:
            result = await client.upload_documents(documents=documents)
            succeeded = sum(1 for r in result if r.succeeded)
            print(f"Upserted {succeeded}/{len(documents)} data records to {DATA_INDEX_NAME} index")
            
            if succeeded < len(documents):
                failed = len(documents) - succeeded
                print(f"Warning: {failed} records failed to upsert")


async def upsert_metadata_batch(records: List[BLSSeriesMetadata]) -> None:
    """
    Upsert a batch of BLS series metadata records to Azure AI Search.
    
    Args:
        records: List of BLSSeriesMetadata objects to upsert
        
    Raises:
        ValueError: If Azure AI Search credentials are not set
        ImportError: If azure-search-documents package is not installed
    """
    if not records:
        print("No metadata records to upsert")
        return
    
    endpoint = _validate_credentials()
    SearchClient, DefaultAzureCredential = _import_azure_search()
    
    # Convert BLSSeriesMetadata objects to dicts for Azure Search
    documents = []
    for record in records:
        doc = {
            "id": record.seriesId,  # Use seriesId as the key
            "seriesId": record.seriesId,
            "name": record.name,
            "category": record.category,
            "level": record.level,
            "state": record.state or "",
            "fips": record.fips or "",
            "county": record.county or "",
            "description": record.description or "",
            "searchable_text": record.searchable_text or ""
        }
        documents.append(doc)
    
    # Upload to Azure AI Search using Managed Identity
    async with DefaultAzureCredential() as credential:
        async with SearchClient(
            endpoint=endpoint,
            index_name=METADATA_INDEX_NAME,
            credential=credential
        ) as client:
            result = await client.upload_documents(documents=documents)
            succeeded = sum(1 for r in result if r.succeeded)
            print(f"Upserted {succeeded}/{len(documents)} metadata records to {METADATA_INDEX_NAME} index")
            
            if succeeded < len(documents):
                failed = len(documents) - succeeded
                print(f"Warning: {failed} records failed to upsert")


async def search_data(
    query: str, 
    top: int = 10,
    filter_expr: Optional[str] = None
) -> List[dict]:
    """
    Search the time series data collection.
    
    Args:
        query: Search query text
        top: Maximum number of results to return
        filter_expr: Optional OData filter expression
                    (e.g., "seriesType eq 'unemployment_rate'")
        
    Returns:
        List of matching documents as dicts
    """
    endpoint = _validate_credentials()
    SearchClient, DefaultAzureCredential = _import_azure_search()
    
    async with DefaultAzureCredential() as credential:
        async with SearchClient(
            endpoint=endpoint,
            index_name=DATA_INDEX_NAME,
            credential=credential
        ) as client:
            results = await client.search(
                search_text=query,
                top=top,
                filter=filter_expr
            )
            return [doc async for doc in results]


async def search_metadata(
    query: str, 
    top: int = 2,
    filter_expr: Optional[str] = None
) -> List[dict]:
    """
    Search the series metadata collection.
    
    Use this for query understanding and series discovery
    (e.g., "find unemployment rate for California").
    
    Args:
        query: Search query text
        top: Maximum number of results to return
        filter_expr: Optional OData filter expression
                    (e.g., "level eq 'state' and state eq 'California'")
        
    Returns:
        List of matching documents as dicts
    """
    endpoint = _validate_credentials()
    SearchClient, DefaultAzureCredential = _import_azure_search()
    
    async with DefaultAzureCredential() as credential:
        async with SearchClient(
            endpoint=endpoint,
            index_name=METADATA_INDEX_NAME,
            credential=credential
        ) as client:
            results = await client.search(
                search_text=query,
                top=top,
                filter=filter_expr
            )
            return [doc async for doc in results]


if __name__ == "__main__":
    import asyncio
    
    # Test vector store manager
    print("Testing Vector Store Manager...")
    print(f"Data Index: {DATA_INDEX_NAME}")
    print(f"Metadata Index: {METADATA_INDEX_NAME}")
    print()
    
    # Check credentials
    try:
        ep = _validate_credentials()
        print("Azure AI Search endpoint is configured")
        print(f"  Endpoint: {ep}")
        print(f"  Authentication: Managed Identity (DefaultAzureCredential)")
        print()
    except ValueError as e:
        print(f"Configuration needed:")
        print(f"   {e}")
        print("\nTo use Azure AI Search, set the endpoint:")
        print("   export AZURE_SEARCH_ENDPOINT='https://your-service.search.windows.net'")
        print("\nAuthentication uses Managed Identity (no API key needed)")
        print()
    
    # Check Azure Search SDK
    try:
        _import_azure_search()
        print("Azure AI Search SDK is installed")
    except ImportError as e:
        print(f"{e}")
        print("\nInstall the package first:")
        print("   pip install azure-search-documents>=11.4.0")
