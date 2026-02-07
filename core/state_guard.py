import logging
import asyncio
import config
from typing import Dict
from enum import Enum, auto
from core.state import State

logger = logging.getLogger("Delio.StateGuard")

class Action(Enum):
    FS_READ = auto()
    FS_WRITE = auto()
    NETWORK = auto()
    DOCKER = auto()
    MEMORY_WRITE = auto()
    MEM_RETRIEVE = auto()
    LLM_CALL = auto()
    SYSTEM_NOTIFICATION = auto()

class StateGuard:
    """
    State transition validator. Locking is owned by FSM (_session_locks).
    StateGuard only validates transitions and checks permissions — no per-user locks.
    """
    def __init__(self):
        self._user_states = {} # user_id -> State

        # Canonical Transitions
        self._allowed_transitions = {
            State.IDLE: [State.OBSERVE, State.NOTIFY],
            State.NOTIFY: [State.IDLE, State.ERROR],
            State.OBSERVE: [State.RETRIEVE, State.PLAN, State.ERROR],
            State.RETRIEVE: [State.PLAN, State.DEEP_THINK, State.ERROR],
            State.DEEP_THINK: [State.DECIDE, State.ERROR],
            State.PLAN: [State.DECIDE, State.ERROR],
            State.DECIDE: [State.ACT, State.RESPOND, State.IDLE, State.ERROR],
            State.ACT: [State.REFLECT, State.ERROR],
            State.RESPOND: [State.REFLECT, State.ERROR],
            State.REFLECT: [State.MEMORY_WRITE, State.PLAN, State.ERROR],
            State.MEMORY_WRITE: [State.IDLE, State.ERROR],
            State.ERROR: [State.IDLE]
        }

        # Side-Effect Matrix (Action -> Allowed States)
        self._side_effect_matrix = {
            Action.FS_READ: [State.OBSERVE, State.ACT],
            Action.FS_WRITE: [State.ACT],
            Action.NETWORK: [State.ACT, State.RESPOND],
            Action.DOCKER: [State.ACT],
            Action.MEMORY_WRITE: [State.MEMORY_WRITE],
            Action.MEM_RETRIEVE: [State.RETRIEVE],
            Action.LLM_CALL: [State.PLAN, State.REFLECT],
            Action.SYSTEM_NOTIFICATION: [State.NOTIFY]
        }

    def get_state(self, user_id: int) -> State:
        return self._user_states.get(user_id, State.IDLE)


    def set_bot(self, bot_instance):
        """Set bot instance for critical alerts."""
        self._bot = bot_instance

    async def _send_alert(self, user_id: int, error: Exception, context: str):
        """Fire-and-forget alert to admin."""
        if hasattr(self, '_bot') and self._bot and config.ADMIN_IDS:
            try:
                msg = f"🚨 **CRITICAL GUARD FAILURE**\nContext: {context}\nUser: `{user_id}`\nError: `{type(error).__name__}: {str(error)}`"
                await self._bot.send_message(config.ADMIN_IDS[0], msg, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")

    async def enter(self, user_id: int, next_state: State):
        """
        Attempt to transition to a new state for a specific user.
        Caller (FSM) must hold the session lock for this user_id.
        """
        current_state = self.get_state(user_id)

        # ANY state can transition to ERROR
        if next_state == State.ERROR:
            logger.warning(f"⚠️ Emergency transition to ERROR for {user_id} from {current_state}")
            self._user_states[user_id] = next_state
            return

        allowed = self._allowed_transitions.get(current_state, [])
        if next_state not in allowed:
            msg = f"❌ FORBIDDEN TRANSITION for {user_id}: {current_state.name} -> {next_state.name}"
            logger.error(msg)
            await self._send_alert(user_id, RuntimeError(msg), "Forbidden Transition")
            self._user_states[user_id] = State.ERROR
            raise RuntimeError(msg)

        logger.debug(f"➡️ StateGuard [{user_id}]: {current_state.name} -> {next_state.name}")
        self._user_states[user_id] = next_state

    async def assert_allowed(self, user_id: int, action: Action):
        """
        Verify if an action is allowed in the user's current state.
        Caller (FSM) must hold the session lock for this user_id.
        """
        current_state = self.get_state(user_id)
        allowed_states = self._side_effect_matrix.get(action, [])
        if current_state not in allowed_states:
            msg = f"🛡️ STATE GUARD BLOCK [{user_id}]: Action {action.name} is FORBIDDEN in {current_state.name}"
            logger.critical(msg)
            await self._send_alert(user_id, PermissionError(msg), f"Action Blocked: {action.name}")
            raise PermissionError(msg)

    def try_enter_notify(self, user_id: int) -> bool:
        """
        Try to enter NOTIFY state only if current state is IDLE.
        Safe in asyncio single-threaded event loop (no await between check and set).
        """
        if self.get_state(user_id) == State.IDLE:
            self._user_states[user_id] = State.NOTIFY
            logger.debug(f"➡️ StateGuard [{user_id}]: IDLE -> NOTIFY (System)")
            return True
        return False

    def force_idle(self, user_id: int):
        """
        Reset the guard to IDLE for a specific user.
        Must be called within FSM session lock.
        """
        self._user_states[user_id] = State.IDLE

    def reset_all_states(self) -> int:
        """
        CRASH AMNESIA: Resets all users to IDLE.
        Thread-unsafe (only call on startup).
        """
        count = len(self._user_states)
        self._user_states.clear()
        return count

# Singleton instance
guard = StateGuard()
