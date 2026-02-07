import logging
import asyncio
from core.state import State
from core.context import ExecutionContext, trace_var
from core.state_guard import guard

MAX_TRANSITIONS = 20
FSM_TIMEOUT_SECONDS = 90

logger = logging.getLogger("Delio.FSM")

class FSMController:
    def __init__(self):
        self.state_handlers = {}
        self.current_state = State.IDLE
        self._session_locks = {}
        self._meta_lock = asyncio.Lock()

    def register_handler(self, state: State, handler):
        self.state_handlers[state] = handler

    async def force_reset_all_users(self):
        """
        CRASH AMNESIA: Forces all users to IDLE state.
        Called on Kernel startup to clean up any zombie states from a previous crash.
        """
        logger.warning("🧹 FSM CRASH AMNESIA: Resetting all user states to IDLE...")
        count = guard.reset_all_states()
        logger.info(f"✅ Reset {count} users to IDLE.")

    async def _get_session_lock(self, user_id: int) -> asyncio.Lock:
        if user_id in self._session_locks:
            return self._session_locks[user_id]
        async with self._meta_lock:
            if user_id not in self._session_locks:
                self._session_locks[user_id] = asyncio.Lock()
            return self._session_locks[user_id]

    async def process_event(self, event_data: dict):
        """
        Main entry point for any external event (message, heartbeat, etc.)
        """
        user_id = event_data.get("user_id", 0)
        context = ExecutionContext(
            user_id=user_id,
            event_type=event_data.get("type", "message"),
            raw_input=event_data.get("text", ""),
            intent=event_data.get("intent", "COMPLEX"),
            metadata=event_data.get("metadata", {})
        )
        
        # Set Trace Context
        token = trace_var.set(context.trace_id)
        
        logger.info(f"🌀 FSM Starting process for user {user_id} (event: {context.event_type})")
        context.add_trace("START")

        session_lock = await self._get_session_lock(user_id)

        # Initial transition
        try:
            # 🔒 SESSION LOCK: Prevent concurrent requests (double clicks, spam)
            if session_lock.locked():
                 logger.warning(f"⏳ User {user_id} session active. Waiting for lock...")

            async with session_lock:
                async with asyncio.timeout(FSM_TIMEOUT_SECONDS):
                    guard.force_idle(user_id) # Safe inside lock
                    await guard.enter(user_id, State.OBSERVE)
                    current_state = State.OBSERVE
                    
                    transitions_count = 0
                    
                    while current_state != State.IDLE:
                        transitions_count += 1
                        if transitions_count > MAX_TRANSITIONS:
                            logger.critical(f"🛑 FSM Loop Limit Exceeded ({MAX_TRANSITIONS}) for user {user_id}")
                            context.errors.append("FSM Loop Limit Exceeded")
                            
                            try:
                                 await guard.enter(user_id, State.ERROR)
                                 current_state = State.ERROR
                            except Exception as e:
                                 logger.critical(f"Critical FSM Failure: {e}")
                                 break
                                 
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
            trace_var.reset(token)
            
        return context

# Singleton instance for the system
instance = FSMController()
