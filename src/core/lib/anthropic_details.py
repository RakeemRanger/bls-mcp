import os

from anthropic import Anthropic, APIError

class AnthropicDetails:
    """Client wrapper for Anthropic API configuration and initialization."""

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Please set it before initializing AnthropicDetails."
            )

    def anthropic_client(self) -> Anthropic:
        try:
            return Anthropic(api_key=self.api_key)
        except APIError as e:
            raise Exception(f"Issue Retrieving Anthropic Client: {e}")
        
    def get_sonnet_model(self, ) -> str:
        client = self.anthropic_client()
        sonnet_models = []
        try:
            claude_models = client.models.list()
            for model in claude_models:
                if "claude-sonnet" in model.id:
                    sonnet_models.append(model.id)
            return str(sonnet_models[0])
        except APIError as e:
            raise Exception(f"Issue Fetching claude-sonnet models: {e}")
        