import sys
from pathlib import Path
from typing import Optional

# Handle imports for both module and script execution
try:
    from augmented.aug import AugmentationManager
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from augmented.aug import AugmentationManager


class GenerationManager:
    """
    Handles the Generation Portion of RAG
    
    Generates structured responses from augmented prompts.
    Enforces professional tone without emojis.
    """
    
    def __init__(self, llm_service=None):
        """
        Initialize generation manager
        
        Args:
            llm_service: Optional LLM service for generation
                        If None, returns augmented prompt only
        """
        self.llm_service = llm_service
        self.system_prompt = self._get_system_prompt()
    
    def _get_system_prompt(self) -> str:
        """
        Get system prompt for BLS data assistant
        
        Returns:
            System prompt string
        """
        return (
            "You are a Bureau of Labor Statistics (BLS) data assistant. "
            "Your role is to provide accurate, factual information about employment, "
            "unemployment, and labor force statistics from the BLS database.\n\n"
            "Guidelines:\n"
            "- Use clear, professional language\n"
            "- Cite specific data points with series names and dates\n"
            "- Explain trends and changes when relevant\n"
            "- If data is insufficient, acknowledge limitations clearly\n"
            "- Provide context about what the numbers represent\n"
            "- When appropriate, explain seasonal adjustments or data collection methods\n\n"
            "Predictive Analysis Capabilities:\n"
            "- When asked predictive questions, analyze historical trends in the provided data\n"
            "- Identify patterns such as upward/downward trends, seasonality, and volatility\n"
            "- Provide reasonable forecasts based on observable trends\n"
            "- Always include clear caveats about forecast uncertainty\n"
            "- Explain factors that might affect future values (economic conditions, policy changes, seasonal effects)\n"
            "- Compare current trends to historical patterns when relevant\n"
            "- Use phrases like 'based on the trend', 'if the pattern continues', 'projecting forward' to indicate forward-looking analysis\n"
            "- Acknowledge that actual future values depend on many unpredictable factors"
        )
    
    async def generate(self, augmented_prompt: str) -> str:
        """
        Generate response from augmented prompt
        
        Args:
            augmented_prompt: Prompt with context from augmentation layer
            
        Returns:
            Generated response string
        """
        if self.llm_service:
            # Generate with LLM
            response = await self.llm_service.get_chat_message_content(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": augmented_prompt}
                ]
            )
            return response.content
        else:
            # Return augmented prompt (for testing)
            return augmented_prompt