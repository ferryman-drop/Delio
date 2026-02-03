import logging
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

class StateGuard:
    def __init__(self):
        self._user_states = {} # user_id -> State
        
        # Canonical Transitions
        self._allowed_transitions = {
            State.IDLE: [State.OBSERVE],
            State.OBSERVE: [State.RETRIEVE, State.PLAN, State.ERROR],
            State.RETRIEVE: [State.PLAN, State.ERROR],
            State.PLAN: [State.DECIDE, State.ERROR],
            State.DECIDE: [State.ACT, State.RESPOND, State.SCHEDULE, State.ERROR],
            State.ACT: [State.REFLECT, State.ERROR],
            State.RESPOND: [State.REFLECT, State.ERROR],
            State.SCHEDULE: [State.REFLECT, State.ERROR],
            State.REFLECT: [State.MEMORY_WRITE, State.ERROR],
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
            Action.LLM_CALL: [State.PLAN, State.REFLECT]
        }

    def get_state(self, user_id: int) -> State:
        return self._user_states.get(user_id, State.IDLE)

    def enter(self, user_id: int, next_state: State):
        """
        Attempt to transition to a new state for a specific user.
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
            self._user_states[user_id] = State.ERROR
            raise RuntimeError(msg)

        logger.debug(f"➡️ StateGuard [{user_id}]: {current_state.name} -> {next_state.name}")
        self._user_states[user_id] = next_state

    def assert_allowed(self, user_id: int, action: Action):
        """
        Verify if an action is allowed in the user's current state.
        """
        current_state = self.get_state(user_id)
        allowed_states = self._side_effect_matrix.get(action, [])
        if current_state not in allowed_states:
            msg = f"🛡️ STATE GUARD BLOCK [{user_id}]: Action {action.name} is FORBIDDEN in {current_state.name}"
            logger.critical(msg)
            raise PermissionError(msg)

    def force_idle(self, user_id: int):
        """Reset the guard to IDLE for a specific user"""
        self._user_states[user_id] = State.IDLE

# Singleton instance
guard = StateGuard()
