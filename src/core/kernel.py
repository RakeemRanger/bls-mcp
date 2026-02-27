import asyncio
import os
from pathlib import Path

from semantic_kernel import Kernel
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.core_plugins.time_plugin import TimePlugin
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from core.tools.info import BlsMcpInformationPlugin
from core.configs.config_loader import AzureConfigLoader


class blsKernel:
    """
    BLS LLM Orchestrator
    """
    def __init__(self, llm_model: str = None, endpoint: str = None, environment: str = None):
        self.kernel = Kernel()
        self.chat_history = ChatHistory()
        
        # Determine environment (dev/prod)
        self.environment = environment or os.getenv('ENVIRONMENT', 'dev')
        
        # Initialize config loader
        try:
            config_loader = AzureConfigLoader(environment=self.environment)
        except Exception as e:
            raise ValueError(
                f"Could not load endpoint. Set AZURE_AI_INFERENCE_ENDPOINT env var or ensure "
                f"resource group ID is configured for '{self.environment}' environment. Error: {e}"
            )
        
        # Get deployment name - priority: parameter > Azure config
        if llm_model:
            self.llm_model = llm_model
        else:
            self.llm_model = config_loader.get_model_deployment()
            if not self.llm_model:
                raise ValueError(f"Could not determine model deployment name for '{self.environment}' environment")
        
        # Get endpoint - priority: parameter > env var > Azure config
        if endpoint:
            self.endpoint = endpoint
        elif os.getenv('AZURE_AI_INFERENCE_ENDPOINT'):
            self.endpoint = os.getenv('AZURE_AI_INFERENCE_ENDPOINT')
        else:
            self.endpoint = config_loader.get_openai_endpoint()
        
        if not self.endpoint:
            raise ValueError(f"No endpoint found for '{self.environment}' environment")
        
        # Initialize services
        self._setup_services()
        self._setup_plugins()

    def _setup_services(self) -> None:
        """Setup LLM service"""
        # Get token provider for Azure AD authentication
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default"
        )
        
        chat_service = AzureChatCompletion(
            deployment_name=self.llm_model,
            endpoint=self.endpoint,
            ad_token_provider=token_provider
        )
        self.kernel.add_service(chat_service)

    def _setup_plugins(self) -> None:
        """Register plugins with kernel"""
        self.kernel.add_plugin(TimePlugin(), plugin_name="TimePlugin")
        self.kernel.add_plugin(BlsMcpInformationPlugin(), plugin_name="BlsMcpInfo")

    def get_execution_settings(self):
        """Get execution settings with function calling enabled"""
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
        settings = OpenAIChatPromptExecutionSettings()
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