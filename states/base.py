from core.state import State
from core.context import ExecutionContext

class BaseState:
    async def execute(self, context: ExecutionContext) -> State:
        raise NotImplementedError("Each state must implement execute")
