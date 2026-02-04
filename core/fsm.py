import logging
import asyncio
from core.state import State
from core.context import ExecutionContext
from core.state_guard import guard

MAX_TRANSITIONS = 20
FSM_TIMEOUT_SECONDS = 30

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
            raw_input=event_data.get("text", ""),
            metadata=event_data.get("metadata", {})
        )
        
        logger.info(f"🌀 FSM Starting process for user {user_id} (event: {context.event_type})")
        context.add_trace("START")

        # Initial transition
        try:
            async with asyncio.timeout(FSM_TIMEOUT_SECONDS):
                guard.force_idle(user_id) # Ensure fresh start
                await guard.enter(user_id, State.OBSERVE)
                current_state = State.OBSERVE
                
                transitions_count = 0
                
                while current_state != State.IDLE:
                    transitions_count += 1
                    if transitions_count > MAX_TRANSITIONS:
                        logger.critical(f"🛑 FSM Loop Limit Exceeded ({MAX_TRANSITIONS}) for user {user_id}")
                        context.errors.append("FSM Loop Limit Exceeded")
                        
                        # Emergency break transition
                        try:
                             # Try to go to ERROR first
                             await guard.enter(user_id, State.ERROR)
                             current_state = State.ERROR
                        except Exception as e:
                             # If even that fails, force break
                             logger.critical(f"Critical FSM Failure: {e}")
                             break
                             
                        # Break loop manually if we are still looping after error usage
                        if transitions_count > MAX_TRANSITIONS + 2:
                            break
                    
                    handler = self.state_handlers.get(current_state)
                    if not handler:
                        logger.error(f"❌ No handler for state: {current_state}")
                        context.errors.append(f"Missing handler for {current_state}")
                        await guard.enter(user_id, State.ERROR)
                        current_state = State.ERROR
                        break
                    
                    logger.debug(f"➡️ User {user_id} entering state: {current_state}")
                    context.add_trace(current_state.name)
                    
                    try:
                        next_state = await handler.execute(context)
                        # Enforce transition through Guard
                        await guard.enter(user_id, next_state)
                        current_state = next_state
                    except Exception as e:
                        logger.exception(f"💥 Error in state {current_state} for user {user_id}: {e}")
                        context.errors.append(str(e))
                        await guard.enter(user_id, State.ERROR)
                        current_state = State.ERROR
                
                logger.info(f"✅ FSM Processed user {user_id}. Trace: {context.trace}")

        except asyncio.TimeoutError:
            logger.critical(f"⏰ FSM Execution Timed Out ({FSM_TIMEOUT_SECONDS}s) for user {user_id}")
            context.errors.append("Processing timed out")

        finally:
            guard.force_idle(user_id)
            guard.cleanup_user_lock(user_id)  # NEW: звільнити lock після завершення
            
        return context

# Singleton instance for the system
instance = FSMController()
