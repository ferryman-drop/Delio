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
    def __init__(self):
        self._user_states = {} # user_id -> State
        self._user_locks: Dict[int, asyncio.Lock] = {}  # NEW
        self._lock_acquisition_lock = asyncio.Lock()    # NEW: meta-lock
        
        # Canonical Transitions
        self._allowed_transitions = {
            State.IDLE: [State.OBSERVE, State.NOTIFY],
            State.NOTIFY: [State.IDLE, State.ERROR],
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
            Action.LLM_CALL: [State.PLAN, State.REFLECT],
            Action.SYSTEM_NOTIFICATION: [State.NOTIFY]
        }

    async def _get_lock(self, user_id: int) -> asyncio.Lock:
        """
        Thread-safe отримання або створення lock для користувача з лімітом MAX_CONCURRENT_USERS.
        Використовує meta-lock для запобігання race condition при створенні locks.
        """
        # Fast path: lock вже існує
        if user_id in self._user_locks:
            logger.debug(f"🔓 Lock retrieved (fast path) for user {user_id}")
            return self._user_locks[user_id]
        
        # Slow path: потрібно створити новий lock
        async with self._lock_acquisition_lock:
            # Double-check pattern (інший task міг створити між перевіркою і lock)
            if user_id not in self._user_locks:
                # Security limit check
                if len(self._user_locks) >= config.MAX_CONCURRENT_USERS:
                    msg = f"🛡️ SECURITY BLOCK: Too many concurrent users ({len(self._user_locks)}). Max: {config.MAX_CONCURRENT_USERS}"
                    logger.critical(msg)
                    raise RuntimeError(msg)
                    
                logger.debug(f"🔒 Creating new lock for user {user_id}")
                self._user_locks[user_id] = asyncio.Lock()
            return self._user_locks[user_id]

    def get_state(self, user_id: int) -> State:
        return self._user_states.get(user_id, State.IDLE)

    async def enter(self, user_id: int, next_state: State):
        """
        Attempt to transition to a new state for a specific user.
        NOW THREAD-SAFE: Uses per-user lock with timeout on acquisition only.
        """
        user_lock = await self._get_lock(user_id)
        
        try:
            # Timeout ТІЛЬКИ на lock acquisition (запобігає partial mutation)
            async with asyncio.timeout(config.STATE_TRANSITION_TIMEOUT):
                await user_lock.acquire()
            
            try:
                # State mutation logic БЕЗ timeout — має завершитися завжди або впасти цілісно
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
            finally:
                user_lock.release()
                    
        except asyncio.TimeoutError:
            logger.critical(f"🔒 DEADLOCK DETECTED for user {user_id}! Lock acquisition timeout after {config.STATE_TRANSITION_TIMEOUT}s")
            # Ми НЕ змінюємо state тут, бо не маємо lock. 
            # FSM.process_event має finally блок, який зробить force_idle()
            raise RuntimeError(f"Lock acquisition timeout for user {user_id}")

    async def assert_allowed(self, user_id: int, action: Action):
        """
        Verify if an action is allowed in the user's current state.
        NOW THREAD-SAFE: Uses per-user lock with timeout on acquisition only.
        """
        user_lock = await self._get_lock(user_id)
        
        try:
            async with asyncio.timeout(config.STATE_TRANSITION_TIMEOUT):
                await user_lock.acquire()
            
            try:
                current_state = self.get_state(user_id)
                allowed_states = self._side_effect_matrix.get(action, [])
                if current_state not in allowed_states:
                    msg = f"🛡️ STATE GUARD BLOCK [{user_id}]: Action {action.name} is FORBIDDEN in {current_state.name}"
                    logger.critical(msg)
                    raise PermissionError(msg)
            finally:
                user_lock.release()
                
        except asyncio.TimeoutError:
            logger.critical(f"🔒 Lock acquisition timeout for user {user_id}")
            raise RuntimeError(f"Lock acquisition timeout for user {user_id}")

    async def try_enter_notify(self, user_id: int) -> bool:
        """
        Try to enter NOTIFY state only if current state is IDLE.
        Non-blocking (short timeout). Returns True if success.
        """
        user_lock = await self._get_lock(user_id)
        try:
            async with asyncio.timeout(0.5):
                await user_lock.acquire()
            try:
                if self.get_state(user_id) == State.IDLE:
                    self._user_states[user_id] = State.NOTIFY
                    logger.debug(f"➡️ StateGuard [{user_id}]: IDLE -> NOTIFY (System)")
                    return True
                return False
            finally:
                user_lock.release()
        except asyncio.TimeoutError:
            return False

    def force_idle(self, user_id: int):
        """Reset the guard to IDLE for a specific user"""
        self._user_states[user_id] = State.IDLE

    def cleanup_user_lock(self, user_id: int):
        """
        Видалити lock користувача після force_idle().
        Викликається після завершення FSM потоку для звільнення пам'яті.
        """
        if user_id in self._user_locks:
            del self._user_locks[user_id]
            logger.debug(f"🧹 Cleaned up lock for user {user_id}")

# Singleton instance
guard = StateGuard()
