from semantic_kernel import Kernel
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.core_plugins.time_plugin import TimePlugin
from semantic_kernel.connectors.ai.anthropic import (
    AnthropicChatCompletion,
    AnthropicChatPromptExecutionSettings
)

from core.lib.anthropic_details import AnthropicDetails
from core.tools.bls_tools import BLSPlugin


SYSTEM_MESSAGE = (
    "You are a Bureau of Labor Statistics assistant. "
    "You help users analyze unemployment and employment public data from the BLS. "
    "Use the BLS tools to look up real data before answering questions about "
    "employment, unemployment, CPI, wages, or other labor statistics. "
    "You can retrieve data at the NATIONAL, STATE, and COUNTY level. "
    "For state queries use the state tool with the state name, abbreviation, or FIPS code. "
    "For county queries use the county tool with the 5-digit county FIPS code. "
    "Use the list_us_states tool if you need to look up a state's FIPS code."
)


class BLSKernel:
    """Semantic Kernel orchestrator for the BLS MCP server."""

    def __init__(self):
        self._llm_details = AnthropicDetails()
        self._kernel = Kernel()
        self._chat_completion = AnthropicChatCompletion(
            ai_model_id=self._llm_details.get_sonnet_model(),
            api_key=self._llm_details.api_key
        )
        self._execution_settings = AnthropicChatPromptExecutionSettings()
        self._execution_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()
        self._chat_history: dict[str, ChatHistory] = {}

        self._kernel.add_plugin(TimePlugin(), "timeTools")
        self._kernel.add_plugin(BLSPlugin(), "blsTools")

    def _get_history(self, session_id: str) -> ChatHistory:
        """Retrieve or create a ChatHistory for the given session."""
        if session_id not in self._chat_history:
            history = ChatHistory()
            history.add_system_message(SYSTEM_MESSAGE)
            self._chat_history[session_id] = history
        return self._chat_history[session_id]

    async def chat(self, user_query: str = None, session_id: str = "default") -> str:
        """
        Process a user query through the BLS agent.

        :param user_query: The user's question or message.
        :type user_query: str
        :param session_id: Unique session identifier for conversation history.
        :type session_id: str
        :return: The agent's response.
        :rtype: str
        """
        if user_query is None:
            return (
                "Hello, I am your Bureau of Labor Stats Agent. "
                "I can help you analyze any data regarding Unemployment "
                "and Employment Public Data."
            )
        history = self._get_history(session_id)
        history.add_user_message(user_query)
        response = await self._chat_completion.get_chat_message_content(
            kernel=self._kernel,
            chat_history=history,
            settings=self._execution_settings
        )
        history.add_message(response)
        return response.content