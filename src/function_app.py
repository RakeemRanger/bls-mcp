import asyncio
import json

import azure.functions as func
import logging

from core.kernel import BLSKernel

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
bls_kernel = BLSKernel()

@app.mcp_tool_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    tool_name="bls_mcp_tool",
    description="Bureau Of Labor Stats Tools Call Endpoint",
    toolProperties='[{"propertyName": "user_query", "propertyType": "string", "description": "The user question about Bureau of Labor Statistics data"}]',
)
def mcp_tool_call(context) -> str:
    content = json.loads(str(context))
    arguments = content.get("arguments", {})
    user_query = arguments.get("user_query")
    logging.info(f"User Query: {user_query}")
    session_id = content.get("sessionid", "default")
    response = asyncio.run(bls_kernel.chat(user_query, session_id))
    logging.info(f"LLM Response: {response}")
    return response
