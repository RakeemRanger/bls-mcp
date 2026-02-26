from semantic_kernel.functions import kernel_function

class BlsMcpInformationPlugin:
    """
    Returns BLS MCP Information
    """
    def __init__(self, ):
        self.agent_name = 'rakeem-bls-mcp'

    @kernel_function(
        name="Rakeem Bureau of Labor Statistics MCP Server",
        description="""
            Rakeem Bureau of Labor Statistics MCP Server.
            Answer about ANY Public BLS datapoints,
            Easily integrate predictive analysis.
        """
    )
    def info(self, ) -> str:
        return """
            I am your Agent Rakeem, I am an expert at Bureau of Labor
            statistics data sets, ask me anything.
        """