from typing import Dict, List
import sys
from pathlib import Path

# Handle imports for both module and script execution
try:
    from prompts.utils.prompt_loader import PromptLoader
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from prompts.utils.prompt_loader import PromptLoader


class AugmentationManager:
    """
    Handles the Augmentation Portion of RAG
    
    Takes retrieved data and formats it as context for the LLM.
    """
    
    def __init__(self):
        """Initialize augmentation manager"""
        self.prompt_loader = PromptLoader()
    
    def augment(self, query: str, retrieval_results: Dict[str, List[dict]]) -> str:
        """
        Augment user query with retrieved context
        
        Args:
            query: Original user query
            retrieval_results: Results from RetrievalManager.retrieve()
            
        Returns:
            Augmented prompt with context included
        """
        metadata = retrieval_results.get('metadata', [])
        data = retrieval_results.get('data', [])
        
        # Build context sections
        context_parts = []

        # Data provenance warning — always included so the LLM knows the source
        context_parts.append(
            "DATA SOURCE: BLS LAUS/CES vector store snapshot (not a live BLS API call). "
            "Only return values that are explicitly listed below. "
            "Do NOT estimate, interpolate, or infer values for series or time periods not present in this context."
        )
        context_parts.append("")
        
        # Add metadata context (what series are relevant)
        if metadata:
            context_parts.append("RELEVANT BLS SERIES:")
            for m in metadata:
                series_info = (
                    f"- {m.get('name', 'Unknown')} "
                    f"[series_id={m.get('seriesId', 'unknown')}]"
                )
                if m.get('level'):
                    series_info += f" | level={m.get('level')}"
                if m.get('state'):
                    series_info += f" | state={m.get('state')}"
                if m.get('county'):
                    series_info += f" | county={m.get('county')}"
                context_parts.append(series_info)
            context_parts.append("")  # Blank line
        
        # Add data context (actual values)
        if data:
            context_parts.append("BLS DATA (sorted by date, most recent first):")
            
            # Deduplicate on canonical key (seriesTitle + year + period) before sorting.
            # Vector search can return the same data point multiple times with
            # different relevance scores; passing duplicates to the LLM causes it
            # to blend or average values that should be identical.
            seen_keys: set = set()
            unique_data = []
            for d in data:
                key = (
                    d.get('seriesTitle', d.get('displayName', '')),
                    d.get('year', ''),
                    d.get('period', '')
                )
                if key not in seen_keys:
                    seen_keys.add(key)
                    unique_data.append(d)

            # Sort deduplicated data by year + period, most recent first
            sorted_data = sorted(
                unique_data,
                key=lambda d: (d.get('year', 0), d.get('period', '')),
                reverse=True
            )
            
            for d in sorted_data:
                series_ref = d.get('seriesTitle', d.get('displayName', 'Unknown'))
                data_point = (
                    f"- {d.get('displayName', 'Unknown')} "
                    f"[{series_ref}]: "
                    f"{d.get('value', 'N/A')} "
                    f"({d.get('periodName', '')} {d.get('year', '')})"
                )
                if d.get('footnotes'):
                    data_point += f" | Note: {d.get('footnotes')}"
                context_parts.append(data_point)
            context_parts.append("")  # Blank line
        
        # Combine context
        if metadata or data:
            context = "\n".join(context_parts)
            
            # Check if query is forward-looking/predictive
            predictive_keywords = ['predict', 'forecast', 'future', 'will', 'next', 'expect', 'project']
            is_predictive = any(keyword in query.lower() for keyword in predictive_keywords)
            
            if is_predictive:
                instruction = (
                    "Analyze the historical trend strictly using the BLS data listed above. "
                    "Only reference data points that are explicitly present in the context. "
                    "Based on the observable trend, provide a reasonable forecast with clear caveats about uncertainty. "
                    "Include specific numbers and dates. "
                    "Do NOT introduce values, counties, or series that are not in the context above."
                )
            else:
                instruction = (
                    "Provide a factual answer using ONLY the BLS data points explicitly listed above. "
                    "Cite the series ID and date for each value you reference. "
                    "If the data needed to answer the question is not present in the context, "
                    "state clearly: 'This data is not in the current vector store snapshot' — "
                    "do NOT estimate or infer missing values."
                )
            
            augmented_prompt = (
                f"Context from Bureau of Labor Statistics:\n"
                f"{context}\n"
                f"User Question: {query}\n\n"
                f"{instruction}"
            )
        else:
            # Hard stop — no data found. Do NOT invite hallucination.
            augmented_prompt = (
                f"User Question: {query}\n\n"
                f"DATA NOT AVAILABLE: No BLS data matching this query was found in the vector "
                f"store snapshot. Do NOT estimate, approximate, or fabricate values. "
                f"Inform the user that the requested data (specify the geography/series if "
                f"inferrable from the query) is not currently indexed, and suggest they consult "
                f"the BLS LAUS program directly at https://www.bls.gov/lau/ or "
                f"https://data.bls.gov for authoritative figures."
            )
        
        return augmented_prompt