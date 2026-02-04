
import asyncio
import sys
import os
import logging
from unittest.mock import MagicMock

# Setup path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'legacy'))

import config
from scheduler import trigger_heartbeat
from core.fsm import instance as fsm
from core.state import State
from core.state_guard import guard
from states.plan import PlanState
from states.decide import DecideState
from states.respond import RespondState
from states.reflect import ReflectState
from states.error import ErrorState

# Log setup
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("TestHeartbeat")

async def main():
    logger.info("🧪 Starting Manual Heartbeat Test")

    # 1. Register States (Minimal set for Heartbeat)
    from states.observe import ObserveState
    from states.retrieve import RetrieveState
    
    fsm.register_handler(State.OBSERVE, ObserveState())
    fsm.register_handler(State.RETRIEVE, RetrieveState())
    fsm.register_handler(State.PLAN, PlanState())
    fsm.register_handler(State.DECIDE, DecideState())
    fsm.register_handler(State.REFLECT, ReflectState())
    
    # Mock Bot for RespondState
    mock_bot = MagicMock()
    async def mock_send(chat_id, text, **kwargs):
        print(f"\n📨 [MOCK TELEGRAM] Send to {chat_id}: {text}\n")
    mock_bot.send_message = mock_send
    
    fsm.register_handler(State.RESPOND, RespondState(mock_bot))
    fsm.register_handler(State.ERROR, ErrorState(mock_bot))

    # 2. Mock state guard to always allow
    # 2. Mock state guard to track state correctly
    mock_states = {}
    def mock_get_state(user_id):
        return mock_states.get(user_id, State.IDLE)
    
    # We also need to ensure entering updates this mock if the real guard.enter uses it?
    # Actually, guard.enter writes to guard._user_states. 
    # If we mock get_state, we must ensure enter writes to the same place or our mock reflects guard._user_states.
    # Better approach: Just don't mock get_state with a lambda. 
    # The real get_state uses self._user_states. Ideally we just reset _user_states.
    pass # Remove the lambda, let the real guard work.

    guard._user_states = {999999: State.IDLE}

    
    # 3. Create a fake active user if none exists
    import sqlite3
    conn = sqlite3.connect('data/chat_history.db')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS messages (user_id INTEGER, timestamp TEXT)")
    # Insert a user active just now
    from datetime import datetime
    cursor.execute("INSERT INTO messages (user_id, timestamp) VALUES (?, ?)", (999999, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

    # 4. Trigger
    logger.info("💓 Invoking trigger_heartbeat()...")
    await trigger_heartbeat()
    
    logger.info("✅ Test Complete")

if __name__ == "__main__":
    asyncio.run(main())
