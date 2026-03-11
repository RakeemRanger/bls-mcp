"""
BLS Data Query Tool - RAG-powered semantic search tool for BLS data
"""

from typing import Annotated
from semantic_kernel.functions import kernel_function
import sys
from pathlib import Path

# Handle imports for both module and script execution
try:
    from rag.rag import RagPipeline
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from rag.rag import RagPipeline


class BlsDataQueryPlugin:
    """
    Kernel plugin for querying BLS data using RAG pipeline
    
    This tool automatically searches Azure AI Search for relevant BLS data
    and provides context-aware responses about employment and unemployment statistics.
    """
    
    def __init__(self):
        """Initialize BLS data query plugin"""
        self.rag_pipeline = None
    
    def _get_rag_pipeline(self):
        """Lazy initialize RAG pipeline"""
        if self.rag_pipeline is None:
            self.rag_pipeline = RagPipeline()
        return self.rag_pipeline
    
    @kernel_function(
        name="query_bls_data",
        description="Search and retrieve Bureau of Labor Statistics employment and unemployment data. Use this for questions about unemployment rates, employment levels, labor force statistics for national, state, or county levels."
    )
    async def query_bls_data(
        self,
        query: Annotated[str, "Natural language query about BLS employment/unemployment data"]
    ) -> Annotated[str, "Retrieved BLS data with context"]:
        """
        Query BLS data using a 3-tier fallback pipeline.

        Resolution order (each tier back-fills the ones above it):
            Tier 1 — Azure AI Search (vector/semantic, fastest)
            Tier 2 — Local disk cache  (JSON files, no network)
            Tier 3 — BLS public API   (live fetch, always complete)

        Back-fill loop:
            T1 hit  → writes cache files  (T2) in background
            T2 hit  → upserts to Azure Search (T1) in background
            T3 hit  → T2 already written by fetcher;
                       upserts to Azure Search (T1) in background

        Args:
            query: User's natural language question about BLS data

        Returns:
            Formatted BLS data context

        Examples:
            - "What is the unemployment rate in California?"
            - "Show me employment trends in Texas for 2024"
            - "Ohio county unemployment rates last 5 years"
        """
        try:
            pipeline = self._get_rag_pipeline()

            # Tiered retrieval (T1 → T2 → T3 with back-fill)
            retrieval_results = await pipeline.retrieval.retrieve(query)

            # Annotate context with which tier served the data
            tier = retrieval_results.pop("tier_used", 0)
            tier_labels = {
                1: "Azure AI Search (vector store)",
                2: "local disk cache",
                3: "BLS public API (live)",
                0: "no data found",
            }
            augmented_context = pipeline.augmentation.augment(query, retrieval_results)
            augmented_context += f"\n\nDATA SOURCE TIER: {tier_labels.get(tier, 'unknown')} (tier {tier})"

            return augmented_context
        except Exception as e:
            return (
                f"Error querying BLS data: {str(e)}\n\n"
                f"This may be due to:\n"
                f"- Azure AI Search not configured (set AZURE_SEARCH_ENDPOINT)\n"
                f"- Vector store not initialized (run scripts/initialize_data.py)\n"
                f"- Network connectivity issues"
            )
