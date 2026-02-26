from azure.identity import DefaultAzureCredential
from azure.ai.inference import ChatCompletionsClient

creds = DefaultAzureCredential()

def client(endpoint: str = None) -> ChatCompletionsClient:
    return ChatCompletionsClient(
        endpoint=endpoint,
        credential=creds
    )