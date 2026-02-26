import azure.functions as func
import logging
import json
import asyncio

from core.kernel import blsKernel

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Initialize kernel once globally
kernel = blsKernel()

@app.mcp_tool_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    tool_name="rakeem_bls_mcp",
    description="""Rakeem Bureau of Labor Statistics MCP Server.
            Answer about ANY Public BLS datapoints,
            Easily integrate predictive analysis.""",
    toolProperties="[]",
)
async def mcp_trigger(context) -> str:
    """
    MCP Tool trigger for BLS queries
    
    Args:
        context: MCP tool context with input arguments
        
    Returns:
        AI response as string
    """
    try:
        # Parse MCP tool input
        # Context structure depends on MCP implementation
        # Common patterns: context.arguments, context.input, or direct dict
        
        if hasattr(context, 'arguments'):
            query = context.arguments.get('query')
        elif isinstance(context, dict):
            query = context.get('query')
        else:
            query = str(context)
        
        logging.info(f"MCP trigger received query: {query}")
        
        # Run query through kernel
        response = asyncio.run(kernel.run(query))
        
        return response
        
    except Exception as e:
        logging.error(f"Error in MCP trigger: {e}")
        return f"Error processing query: {str(e)}"
