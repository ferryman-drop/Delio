import asyncio
import logging
import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../legacy')))

from core.fsm import instance as fsm
from core.state import State
from core.state_guard import guard, Action
from core.context import ExecutionContext

# Mocking bot for testing
class MockBot:
    async def send_message(self, chat_id, text):
        print(f"📡 [MOCK BOT] Sending to {chat_id}: {text[:50]}...")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFIER")

async def test_fsm_cycle():
    print("\n--- 🏁 TEST 1: FSM Cognitive Cycle ---")
    mock_ctx = ExecutionContext(user_id=123, event_type="message", raw_input="Hello AID, remember I like coffee")
    
    # We need to register minimal handlers if not in main.py
    # Since we imported 'fsm' instance, we assume it might be empty if main hasn't run.
    # But FSM is a singleton, and we want to test the REAL registered handlers.
    
    # Let's manually register for the test script scope to be sure
    from states.observe import ObserveState
    from states.retrieve import RetrieveState
    from states.plan import PlanState
    from states.decide import DecideState
    from states.respond import RespondState
    from states.reflect import ReflectState
    from states.memory_write import MemoryWriteState
    
    fsm.register_handler(State.OBSERVE, ObserveState())
    fsm.register_handler(State.RETRIEVE, RetrieveState())
    fsm.register_handler(State.PLAN, PlanState())
    fsm.register_handler(State.DECIDE, DecideState())
    fsm.register_handler(State.ACT, RespondState(MockBot())) # Use Respond as Act for neutral test
    fsm.register_handler(State.RESPOND, RespondState(MockBot()))
    fsm.register_handler(State.REFLECT, ReflectState())
    fsm.register_handler(State.MEMORY_WRITE, MemoryWriteState())

    result_ctx = await fsm.process_event({
        "user_id": 123,
        "type": "message",
        "text": "Verification test message."
    })
    
    print(f"✅ Trace: {' -> '.join(result_ctx.trace)}")
    has_plan = any("PLAN" in t for t in result_ctx.trace)
    has_reflect = any("REFLECT" in t for t in result_ctx.trace)
    
    if has_plan and has_reflect:
        print("🟢 FSM Lifecycle Verified.")
    else:
        print("🔴 FSM Lifecycle Failure.")

async def test_state_guard_blocking():
    print("\n--- 🛡️ TEST 2: State Guard Enforcement ---")
    guard.force_idle()
    
    # Test 2.1: Action out of state
    try:
        guard.enter(State.OBSERVE)
        print("Current State: OBSERVE. Attempting LLM call (should fail)...")
        guard.assert_allowed(Action.LLM_CALL)
        print("🔴 FAILURE: Guard allowed LLM call in OBSERVE.")
    except PermissionError as e:
        print(f"✅ SUCCESS: Guard blocked action: {e}")

    # Test 2.2: Illegal transition
    try:
        print("Attempting Illegal Transition: OBSERVE -> ACT (skipping PLAN/DECIDE)...")
        guard.enter(State.ACT)
        print("🔴 FAILURE: Guard allowed OBSERVE -> ACT.")
    except RuntimeError as e:
        print(f"✅ SUCCESS: Guard blocked transition: {e}")
        
    guard.force_idle()

async def main():
    print("🚀 AID KERNEL VERIFICATION SUITE STARTING")
    
    await test_state_guard_blocking()
    # FSM Cycle might call real LLM, so we skip or mock if possible
    # But for a real "is it alive" check, we want a real run.
    # To avoid spending credits during every check, let's keep it optional.
    
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        await test_fsm_cycle()
    
    print("\n🏁 VERIFICATION COMPLETE.")

if __name__ == "__main__":
    asyncio.run(main())
