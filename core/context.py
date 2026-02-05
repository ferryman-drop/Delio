from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from contextvars import ContextVar

trace_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)

@dataclass
class ExecutionContext:
    user_id: Optional[int] = None
    event_type: str = "message"
    raw_input: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    trace_id: str = field(default_factory=lambda: str(__import__('uuid').uuid4()))
    
    # State-specific data
    metadata: Dict[str, Any] = field(default_factory=dict)
    memory_context: Dict[str, Any] = field(default_factory=dict)
    plan: Optional[Any] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_outputs: List[Dict[str, Any]] = field(default_factory=list)
    act_results: List[Any] = field(default_factory=list)
    response: str = ""
    
    # Execution markers
    errors: List[str] = field(default_factory=list)
    trace: List[str] = field(default_factory=list)

    def add_trace(self, state_name: str):
        self.trace.append(f"{datetime.now().isoformat()} - {state_name}")
