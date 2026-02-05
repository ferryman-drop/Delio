
import asyncio
import logging
import sys
import os
import time

# Setup path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'legacy'))

import config
from core import logger as core_logger
from core.fsm import instance as fsm
from core.state import State
from core.state_guard import guard
from states.base import BaseState
from unittest.mock import MagicMock, AsyncMock

# Setup logging
core_logger.setup_logging("logs/test_trace.json", level="DEBUG")
logger = logging.getLogger("TestTrace")

class MockState(BaseState):
    async def execute(self, context):
        logger.info(f"Executing MockState for trace {context.trace_id}")
        return State.IDLE

class CrashState(BaseState):
    async def execute(self, context):
        raise RuntimeError("Create Crash for Alert Test")

async def test_trace():
    print("--- 1. Testing Trace Injection ---")
    
    # Mock handlers
    fsm.register_handler(State.OBSERVE, MockState())
    fsm.register_handler(State.IDLE, MockState())
    
    # Run FSM
    await fsm.process_event({
        "user_id": 111,
        "type": "message",
        "text": "Hello Trace"
    })
    
    # Check log file
    time.sleep(1)
    with open("logs/test_trace.json", 'r') as f:
        logs = f.readlines()
        
    found_trace = False
    for line in logs:
        if "Executing MockState" in line and '"trace_id":' in line:
             if "null" not in line:
                 found_trace = True
                 print(f"✅ Found trace in log: {line.strip()[:100]}...")
                 break
    
    if not found_trace:
        print("❌ Trace ID not found in logs!")

async def test_alert():
    print("\n--- 2. Testing Alert Mechanism ---")
    
    # Mock Bot
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()
    
    # Set bot in guard
    guard.set_bot(mock_bot)
    
    # Trigger Forbidden Transition manually to force alert
    try:
        # IDLE -> RESPOND is forbidden (IDLE -> OBSERVE/NOTIFY only)
        # We need to simulate this call on the guard
        await guard.enter(222, State.RESPOND) 
    except RuntimeError:
        print("Caught expected RuntimeError")
        
    # Check if send_message was called
    if mock_bot.send_message.called:
        print("✅ Alert sent via mock bot.")
        args = mock_bot.send_message.call_args
        print(f"Message content: {args[0][1]}")
    else:
        print("❌ Alert NOT sent.")

if __name__ == "__main__":
    asyncio.run(test_trace())
    asyncio.run(test_alert())
