import asyncio
import os

from semantic_kernel import Kernel
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.core_plugins.time_plugin import TimePlugin
from semantic_kernel.connectors.ai.azure_ai_inference import (
    AzureAIInferenceChatCompletion,
    AzureAIInferencePromptExecutionSettings
)
from utils.chat_completion_client import client
from tools.info import BlsMcpInformationPlugin


class blsKernel:
    """
    BLS LLM Orchestrator
    """
    def __init__(self, llm_model: str = 'gpt-4o', endpoint: str = None):
        self.kernel = Kernel()
        self.chat_history = ChatHistory()
        self.llm_model = llm_model
        self.endpoint = endpoint or os.getenv('AZURE_AI_INFERENCE_ENDPOINT')
        
        # Initialize services
        self._setup_services()
        self._setup_plugins()

    def _setup_services(self) -> None:
        """Setup LLM service"""
        chat_service = AzureAIInferenceChatCompletion(
            ai_model_id=self.llm_model,
            client=client(endpoint=self.endpoint)
        )
        self.kernel.add_service(chat_service)

    def _setup_plugins(self) -> None:
        """Register plugins with kernel"""
        self.kernel.add_plugin(TimePlugin(), plugin_name="TimePlugin")
        self.kernel.add_plugin(BlsMcpInformationPlugin(), plugin_name="BlsMcpInfo")

    def get_execution_settings(self) -> AzureAIInferencePromptExecutionSettings:
        """Get execution settings with function calling enabled"""
        settings = AzureAIInferencePromptExecutionSettings()
        settings.function_choice_behavior = FunctionChoiceBehavior.Auto()
        return settings

    async def run(self, query: str = None) -> str:
        """
        Run a query through the kernel
        
        Args:
            query: User query string. If None, returns greeting.
            
        Returns:
            Response string from the LLM
        """
        if query is None:
            greeting = BlsMcpInformationPlugin()
            return greeting.info()
        
        # Add user message to history
        self.chat_history.add_user_message(query)
        
        try:
            # Get chat service
            chat_service = self.kernel.get_service()
            
            # Get response
            response = await chat_service.get_chat_message_content(
                chat_history=self.chat_history,
                settings=self.get_execution_settings(),
                kernel=self.kernel
            )
            
            # Add response to history
            self.chat_history.add_message(response)
            
            return response.content
            
        except Exception as e:
            raise Exception(f"Issue fetching answer: {e}")
        

if __name__ == '__main__':
    chat = blsKernel()
    print(asyncio.run(chat.run('')))