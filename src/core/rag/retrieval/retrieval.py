from typing import List, Dict, Optional
import sys
from pathlib import Path

# Handle imports for both module and script execution
try:
    from rag.data import vector_store_manager
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from rag.data import vector_store_manager


class RetrievalManager:
    """
    Handles the Retrieval Portion of RAG
    
    Two-stage retrieval:
    1. Search metadata to understand what series the user wants
    2. Search data to get actual values for those series
    """
    
    def __init__(self, max_metadata_results: int = 8, max_data_results: int = 40):
        """
        Initialize retrieval manager
        
        Args:
            max_metadata_results: Max series to identify from metadata search
            max_data_results: Max data points to retrieve per query
        """
        self.max_metadata_results = max_metadata_results
        self.max_data_results = max_data_results
    
    async def retrieve(self, query: str) -> Dict[str, List[dict]]:
        """
        Retrieve relevant BLS data for a user query
        
        Args:
            query: Natural language query (e.g., "California unemployment rate")
            
        Returns:
            Dict with 'metadata' and 'data' keys containing search results
        """
        # Stage 1: Search metadata to understand what series user wants
        metadata_results = await vector_store_manager.search_metadata(
            query=query,
            top=self.max_metadata_results
        )
        
        if not metadata_results:
            return {
                'metadata': [],
                'data': []
            }
        
        # Extract series IDs from metadata
        series_ids = [m.get('seriesId') for m in metadata_results if m.get('seriesId')]
        
        # Stage 2: Search data for those specific series
        # Build filter to match any of the identified series
        if series_ids:
            # Also search data collection with original query + series filter
            data_results = await vector_store_manager.search_data(
                query=query,
                top=self.max_data_results,
                filter_expr=self._build_series_filter(series_ids)
            )
        else:
            # Fallback: just search data with query
            data_results = await vector_store_manager.search_data(
                query=query,
                top=self.max_data_results
            )
        
        return {
            'metadata': metadata_results,
            'data': data_results
        }
    
    def _build_series_filter(self, series_ids: List[str]) -> str:
        """
        Build OData filter expression for multiple series IDs
        
        Args:
            series_ids: List of series IDs to include
            
        Returns:
            OData filter string like "seriesTitle eq 'LNS14000000' or seriesTitle eq 'LASST060000000003'"
        """
        if not series_ids:
            return None
        
        # Build OR filter for all series IDs
        # seriesId field stores unique keys like 'LNS14000000_2024_M01',
        # so full-text ismatch on the bare series ID matches all its data points.
        filters = [f"search.ismatch('{sid}', 'seriesId')" for sid in series_ids[:10]]  # Allow up to 10 series
        return " or ".join(filters)