import logging
from core.state import State
from core.context import ExecutionContext
from core.state_guard import guard

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
        user_id = event_data.get("user_id", 0)
        context = ExecutionContext(
            user_id=user_id,
            event_type=event_data.get("type", "message"),
            raw_input=event_data.get("text", "")
        )
        
        logger.info(f"🌀 FSM Starting process for user {user_id} (event: {context.event_type})")
        context.add_trace("START")

        # Initial transition
        try:
            guard.force_idle(user_id) # Ensure fresh start
            guard.enter(user_id, State.OBSERVE)
            current_state = State.OBSERVE
            
            while current_state != State.IDLE:
                handler = self.state_handlers.get(current_state)
                if not handler:
                    logger.error(f"❌ No handler for state: {current_state}")
                    context.errors.append(f"Missing handler for {current_state}")
                    guard.enter(user_id, State.ERROR)
                    current_state = State.ERROR
                    break
                
                logger.debug(f"➡️ User {user_id} entering state: {current_state}")
                context.add_trace(current_state.name)
                
                try:
                    next_state = await handler.execute(context)
                    # Enforce transition through Guard
                    guard.enter(user_id, next_state)
                    current_state = next_state
                except Exception as e:
                    logger.exception(f"💥 Error in state {current_state} for user {user_id}: {e}")
                    context.errors.append(str(e))
                    guard.enter(user_id, State.ERROR)
                    current_state = State.ERROR
            
            logger.info(f"✅ FSM Processed user {user_id}. Trace: {context.trace}")
        finally:
            guard.force_idle(user_id)
            
        return context

# Singleton instance for the system
instance = FSMController()
