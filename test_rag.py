#!/usr/bin/env python3
"""
Test RAG Pipeline Components

This script tests each layer of the RAG pipeline independently.
Run after Azure AI Search is configured and data is initialized.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.rag.retrieval.retrieval import RetrievalManager
from core.rag.augmented.aug import AugmentationManager
from core.rag.generation.gen import GenerationManager
from core.rag.rag import RagPipeline


async def test_retrieval():
    """Test retrieval layer"""
    print("=" * 60)
    print("TEST 1: RETRIEVAL LAYER")
    print("=" * 60)
    
    try:
        retrieval = RetrievalManager(max_metadata_results=3, max_data_results=10)
        query = "California unemployment rate"
        
        print(f"Query: {query}")
        print("Searching Azure AI Search...")
        
        results = await retrieval.retrieve(query)
        
        print(f"\nMetadata results: {len(results['metadata'])} series found")
        for m in results['metadata'][:3]:
            print(f"  - {m.get('name', 'Unknown')} [{m.get('seriesId', '')}]")
        
        print(f"\nData results: {len(results['data'])} data points found")
        for d in results['data'][:5]:
            print(f"  - {d.get('displayName', 'Unknown')}: {d.get('value', 'N/A')} ({d.get('periodName', '')} {d.get('year', '')})")
        
        print("\nRetrieval test PASSED")
        return results
        
    except Exception as e:
        print(f"\nRetrieval test FAILED: {e}")
        return None


async def test_augmentation(retrieval_results):
    """Test augmentation layer"""
    print("\n" + "=" * 60)
    print("TEST 2: AUGMENTATION LAYER")
    print("=" * 60)
    
    try:
        augmentation = AugmentationManager()
        query = "California unemployment rate"
        
        if retrieval_results is None:
            print("Skipping (no retrieval results)")
            return None
        
        print(f"Query: {query}")
        print("Augmenting with retrieved context...")
        
        augmented = augmentation.augment(query, retrieval_results)
        
        print("\nAugmented prompt:")
        print("-" * 60)
        print(augmented[:500] + "..." if len(augmented) > 500 else augmented)
        print("-" * 60)
        
        print("\nAugmentation test PASSED")
        return augmented
        
    except Exception as e:
        print(f"\nAugmentation test FAILED: {e}")
        return None


async def test_full_pipeline():
    """Test complete RAG pipeline"""
    print("\n" + "=" * 60)
    print("TEST 3: COMPLETE RAG PIPELINE")
    print("=" * 60)
    
    try:
        pipeline = RagPipeline()
        query = "What is the unemployment rate in Texas?"
        
        print(f"Query: {query}")
        print("Processing through RAG pipeline...")
        
        details = await pipeline.process_with_details(query)
        
        print(f"\nRetrieval: {len(details['retrieval']['metadata'])} series, {len(details['retrieval']['data'])} data points")
        print(f"Augmented prompt: {len(details['augmented_prompt'])} characters")
        print(f"Response: {len(details['response'])} characters")
        
        print("\nResponse preview:")
        print("-" * 60)
        print(details['response'][:500] + "..." if len(details['response']) > 500 else details['response'])
        print("-" * 60)
        
        print("\nFull pipeline test PASSED")
        
    except Exception as e:
        print(f"\nFull pipeline test FAILED: {e}")


async def test_kernel_tool():
    """Test kernel tool integration"""
    print("\n" + "=" * 60)
    print("TEST 4: KERNEL TOOL")
    print("=" * 60)
    
    try:
        from core.tools.bls_data_tool import BlsDataQueryPlugin
        
        tool = BlsDataQueryPlugin()
        query = "unemployment rate in Florida"
        
        print(f"Query: {query}")
        print("Calling kernel tool...")
        
        result = await tool.query_bls_data(query)
        
        print("\nTool result:")
        print("-" * 60)
        print(result[:500] + "..." if len(result) > 500 else result)
        print("-" * 60)
        
        print("\nKernel tool test PASSED")
        
    except Exception as e:
        print(f"\nKernel tool test FAILED: {e}")


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("RAG PIPELINE TEST SUITE")
    print("=" * 60)
    print("Prerequisites:")
    print("- Azure AI Search configured (AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY)")
    print("- Data initialized (python3 scripts/initialize_data.py)")
    print("=" * 60)
    
    # Test 1: Retrieval
    retrieval_results = await test_retrieval()
    
    # Test 2: Augmentation
    augmented = await test_augmentation(retrieval_results)
    
    # Test 3: Full pipeline
    await test_full_pipeline()
    
    # Test 4: Kernel tool
    await test_kernel_tool()
    
    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
