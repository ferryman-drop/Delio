from states.base import BaseState
from core.state import State
from core.context import ExecutionContext

class ObserveState(BaseState):
    async def execute(self, context: ExecutionContext) -> State:
        # For now, just a placeholder for input normalization
        # In the future, this will handle voice transcription, file parsing, etc.
        if not context.raw_input:
            context.errors.append("Empty input in OBSERVE")
            return State.IDLE
            
        return State.RETRIEVE
