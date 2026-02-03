from datetime import datetime
from core.tool_registry import BaseTool, ToolDefinition, registry

class GetTimeTool(BaseTool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_time",
            description="Get the current current date and time in ISO format.",
            parameters={
                "type": "object",
                "properties": {}
            },
            requires_confirmation=False
        )

    async def execute(self, **kwargs) -> str:
        return datetime.now().isoformat()

# Auto-register
registry.register(GetTimeTool())
