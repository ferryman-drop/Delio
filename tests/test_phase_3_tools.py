import pytest
from core.tool_registry import ToolRegistry, BaseTool, ToolDefinition

# Mock Tool
class MockTool(BaseTool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="mock_tool",
            description="A mock tool for testing",
            parameters={"type": "object", "properties": {"foo": {"type": "string"}}}
        )

    async def execute(self, **kwargs):
        return f"Mock executed with {kwargs}"

@pytest.fixture
def clean_registry():
    # Use a fresh registry instance for testing instead of singleton
    return ToolRegistry()

@pytest.mark.asyncio
async def test_registry_registration(clean_registry):
    tool = MockTool()
    clean_registry.register(tool)
    
    retrieved = clean_registry.get_tool("mock_tool")
    assert retrieved is not None
    assert retrieved.definition.name == "mock_tool"

@pytest.mark.asyncio
async def test_get_definitions(clean_registry):
    tool = MockTool()
    clean_registry.register(tool)
    
    defs = clean_registry.get_definitions()
    assert len(defs) == 1
    assert defs[0]['name'] == 'mock_tool'
    assert defs[0]['parameters']['properties']['foo']['type'] == 'string'

@pytest.mark.asyncio
async def test_tool_overwriting(clean_registry):
    tool1 = MockTool()
    clean_registry.register(tool1)
    
    # Register same name again
    clean_registry.register(tool1)
    assert len(clean_registry._tools) == 1

@pytest.mark.asyncio
async def test_tool_execution():
    tool = MockTool()
    result = await tool.execute(foo="bar")
    assert result == "Mock executed with {'foo': 'bar'}"
