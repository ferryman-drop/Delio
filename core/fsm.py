import logging
from core.state import State
from core.context import ExecutionContext

logger = logging.getLogger("Delio.FSM")

class FSMController:
    def __init__(self):
        self.state_handlers = {}
        self.current_state = State.IDLE

    def register_handler(self, state: State, handler):
        self.state_handlers[state] = handler

    async def process_event(self, event_data: dict):
        """
        Main entry point for any external event (message, heartbeat, etc.)
        """
        context = ExecutionContext(
            user_id=event_data.get("user_id"),
            event_type=event_data.get("type", "message"),
            raw_input=event_data.get("text", "")
        )
        
        logger.info(f"🌀 FSM Starting process for event: {context.event_type}")
        context.add_trace("START")

        # Initial state
        self.current_state = State.OBSERVE
        
        while self.current_state != State.IDLE:
            handler = self.state_handlers.get(self.current_state)
            if not handler:
                logger.error(f"❌ No handler for state: {self.current_state}")
                context.errors.append(f"Missing handler for {self.current_state}")
                break
            
            logger.debug(f"➡️ Entering state: {self.current_state}")
            context.add_trace(self.current_state.name)
            
            try:
                next_state = await handler.execute(context)
                self.current_state = next_state
            except Exception as e:
                logger.exception(f"💥 Error in state {self.current_state}: {e}")
                context.errors.append(str(e))
                self.current_state = State.IDLE # Or error handling state
        
        logger.info(f"✅ FSM Processed. Errors: {len(context.errors)}")
        return context
