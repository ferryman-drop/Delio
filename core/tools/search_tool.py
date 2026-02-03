from core.tool_registry import BaseTool, ToolDefinition, registry
from tools import search_web
import logging

class WebSearchTool(BaseTool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description="Search the internet for information, news, and facts. Returns snippets and links.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default is 5).",
                        "default": 5
                    }
                },
                "required": ["query"]
            },
            requires_confirmation=False
        )

    async def execute(self, **kwargs) -> str:
        # Note: we need 'user_id' here. 
        # The execution layer (ACT state) should inject system-level context.
        user_id = kwargs.get("user_id")
        query = kwargs.get("query")
        max_results = kwargs.get("max_results", 5)
        
        if not user_id:
            return "❌ Internal Error: user_id missing in tool execution."
            
        return await search_web(query, user_id, max_results)

# Auto-register
registry.register(WebSearchTool())
