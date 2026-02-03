from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger("Delio.ToolRegistry")

@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any] # JSON Schema
    requires_confirmation: bool = False

class BaseTool(ABC):
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        pass

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        if tool.definition.name in self._tools:
            logger.warning(f"Overwriting tool '{tool.definition.name}' in registry.")
        self._tools[tool.definition.name] = tool
        logger.debug(f"Registered tool: {tool.definition.name}")
        
    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)
        
    def get_definitions(self) -> List[Dict]:
        return [t.definition.__dict__ for t in self._tools.values()]
    
# Singleton instance
registry = ToolRegistry()
