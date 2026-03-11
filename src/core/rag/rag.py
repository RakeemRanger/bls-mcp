from typing import Dict, Any, Optional
import sys
from pathlib import Path

# Handle imports for both module and script execution
try:
    from rag.retrieval.tiered_retrieval import TieredRetrievalManager
    from rag.augmented.aug import AugmentationManager
    from rag.generation.gen import GenerationManager
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from rag.retrieval.tiered_retrieval import TieredRetrievalManager
    from rag.augmented.aug import AugmentationManager
    from rag.generation.gen import GenerationManager


class RagPipeline:
    """
    Complete RAG Pipeline for BLS Data Queries
    
    Orchestrates retrieval, augmentation, and generation stages.
    """
    
    def __init__(self, llm_service=None):
        """
        Initialize RAG pipeline
        
        Args:
            llm_service: Optional LLM service for generation
        """
        self.retrieval = TieredRetrievalManager()
        self.augmentation = AugmentationManager()
        self.generation = GenerationManager(llm_service=llm_service)
    
    async def process(self, query: str) -> str:
        """
        Process a user query through the complete RAG pipeline
        
        Args:
            query: User's natural language query
            
        Returns:
            Generated response with BLS data context
        """
        # Stage 1: Retrieve relevant data from vector store
        retrieval_results = await self.retrieval.retrieve(query)
        
        # Stage 2: Augment query with retrieved context
        augmented_prompt = self.augmentation.augment(query, retrieval_results)
        
        # Stage 3: Generate response
        response = await self.generation.generate(augmented_prompt)
        
        return response
    
    async def process_with_details(self, query: str) -> Dict[str, Any]:
        """
        Process query and return detailed results from each stage
        
        Args:
            query: User's natural language query
            
        Returns:
            Dict with results from each pipeline stage
        """
        # Stage 1: Retrieve
        retrieval_results = await self.retrieval.retrieve(query)
        
        # Stage 2: Augment
        augmented_prompt = self.augmentation.augment(query, retrieval_results)
        
        # Stage 3: Generate
        response = await self.generation.generate(augmented_prompt)
        
        return {
            'query': query,
            'retrieval': retrieval_results,
            'augmented_prompt': augmented_prompt,
            'response': response
        }


# Legacy alias for backward compatibility
RagResults = RagPipeline