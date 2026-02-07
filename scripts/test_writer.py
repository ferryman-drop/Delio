import sys
sys.path.append("/root/ai_assistant")
import asyncio
from core.tools.obsidian_tools import ObsidianTool
from core.state_guard import guard, State

async def test_writer():
    tool = ObsidianTool()
    user_id = 99999
    
    # Mock Guard state for permission (Need lock)
    # Actually, the tool calls guard.assert_allowed
    # We need to be in a state that allows FS_WRITE (e.g., ACT)
    # But guard requires lock.
    
    # Let's bypass guard mock for unit test?
    # Or just set state properly.
    
    try:
        # Mocking Guard: We need to enter state first
        # But guard is singleton.
        await guard._get_lock(user_id) # Ensure lock exists
        guard._user_states[user_id] = State.ACT # ACT allows FS_WRITE
        
        print("1. Testing CREATE...")
        res = await tool.execute(
            action="create", 
            filename="Test Writer.md", 
            content="# Hello Writer\nThis is a test.", 
            user_id=user_id
        )
        print(f"Result: {res}")
        
        print("\n2. Testing APPEND...")
        res = await tool.execute(
            action="append", 
            filename="Test Writer.md", 
            content="Appended line.", 
            user_id=user_id
        )
        print(f"Result: {res}")
        
        print("\n3. Testing READ...")
        res = await tool.execute(
            action="read", 
            filename="Test Writer.md", 
            user_id=user_id
        )
        print(f"Result: {res}")

    except Exception as e:
        print(f"Test Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_writer())
