# Implementation Plan: Autonomous Agent (Phase 3.0)

## Goal
Enable the AI Assistant to autonomously select and execute tools to fulfill user requests, moving beyond simple conversational responses.

## User Review Required
> [!IMPORTANT]
> **Tool Execution Permissions**: Some tools (like file system write or extensive network access) may require explicit user confirmation. We will implement a `requires_confirmation` flag in the Tool definition.

> [!WARNING]
> **Model Behavior Change**: The Actor model will now be instructed to output JSON tool calls. This might temporarily affect the conversational quality if not balanced correctly. We need to monitor for "JSON leakage" into chat.

## Proposed Changes

### 1. Core Module: Tooling Infrastructure

#### [NEW] `core/tool_registry.py`
Create a robust registry to manage all available tools.
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass

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
        self._tools[tool.definition.name] = tool
        
    def get_tool(self, name: str) -> BaseTool:
        return self._tools.get(name)
        
    def get_definitions(self) -> List[Dict]:
        return [t.definition.__dict__ for t in self._tools.values()]
    
    # Singleton instance
registry = ToolRegistry()
```

### 2. Cognitive State: ACT

#### [MODIFY] `states/act.py`
Currently this state is likely a stub. We need to implement the execution logic.

1.  **Input**: Receives `tool_calls` list from `ExecutionContext` (populated by `DECIDE` state).
2.  **Process**:
    - Iterate through tool calls.
    - Validate tool existence in `ToolRegistry`.
    - Check permissions (if `requires_confirmation`, maybe wait? For Phase 3.0 start, we might skip UI confirmation or fail safe).
    - Execute `tool.execute(**args)`.
3.  **Output**:
    - Store tool results in `ExecutionContext.tool_outputs`.
    - Transition to `REFLECT` (to analyze result) or `RESPOND` (to show result).

### 3. Cognitive State: PLAN & DECIDE

#### [MODIFY] `states/plan.py`
1.  **System Prompt Injection**:
    - Inject `tool_registry.get_definitions()` into the system instruction so the LLM knows what tools are available.
    - Add instructions: "If you need to use a tool, output a JSON block..."

2.  **Parsing**:
    - While `PLAN` generates the thought process, `DECIDE` (or the end of `PLAN`) must parse the output to extract:
        - Thought
        - Tool Call (Name + Args)

#### [MODIFY] `states/decide.py`
1.  **Logic Update**:
    - If `context.tool_calls` is present -> Transition to `ACT`.
    - Else -> Transition to `RESPOND`.

### 4. Tool Implementations

#### [MODIFY] `tools/search.py` (or similar)
- Wrap existing search logic into `class WebSearchTool(BaseTool)`.

#### [NEW] `tools/time.py`
- Simple `GetTimeTool` for testing.

## Verification Plan

### Automated Tests
1.  **Registry Test**: Register a mock tool and retrieve it.
2.  **Execution Test**: Execute a mock tool via `ACT` state handler.
3.  **Parsing Test**: Feed a sample LLM JSON response to `PLAN` parser and verify `tool_calls` are extracted correctly.

### Manual Verification
1.  **Scenario: "What time is it?"**
    - LLM should call `get_time`.
    - `ACT` executes it.
    - Bot responds with correct time.
    - **Success Criteria**: No crash, correct time displayed.

2.  **Scenario: "Search for DeepSeek V3 release date"**
    - LLM calls `web_search`.
    - `ACT` executes.
    - Bot summarizes search results.

## Rollback Plan
- Phase 3.0 involves meaningful code additions.
- If FSM breaks, revert `states/plan.py` prompt changes and disable `ACT` transitions (return to IDLE or RESPOND directly).
