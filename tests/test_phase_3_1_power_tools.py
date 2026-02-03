import pytest
import os
import shutil
from unittest.mock import AsyncMock, patch, MagicMock
from core.tool_registry import registry
from core.tools.note_tool import NoteTool
from core.tools.reminder_tool import ReminderTool
from datetime import datetime

@pytest.fixture
def note_tool():
    return NoteTool()

@pytest.fixture
def reminder_tool():
    return ReminderTool()

@pytest.mark.asyncio
async def test_note_tool_ops(note_tool):
    from core.state_guard import guard
    from core.state import State
    user_id = 777
    
    # Pre-requisite: Enter ACT state to allow FS_WRITE/READ
    await guard.enter(user_id, State.OBSERVE)
    await guard.enter(user_id, State.RETRIEVE)
    await guard.enter(user_id, State.PLAN)
    await guard.enter(user_id, State.DECIDE)
    await guard.enter(user_id, State.ACT)
    
    note_name = "test_note"
    note_content = "Hello notes world"
    
    # 1. Write
    res = await note_tool.execute(action="write", name=note_name, content=note_content, user_id=user_id)
    assert "збережено" in res
    
    # Check physical file
    path = os.path.join("data/notes", str(user_id), f"{note_name}.txt")
    assert os.path.exists(path)
    
    # 2. List
    res = await note_tool.execute(action="list", user_id=user_id)
    assert note_name in res
    
    # 3. Read
    res = await note_tool.execute(action="read", name=note_name, user_id=user_id)
    assert note_content in res
    
    # Cleanup
    shutil.rmtree(os.path.join("data/notes", str(user_id)))
    guard.cleanup_user_lock(user_id)

@pytest.mark.asyncio
async def test_reminder_tool_parsing(reminder_tool):
    from core.state_guard import guard
    from core.state import State
    user_id = 888
    
    # Enter ACT state to allow NETWORK
    await guard.enter(user_id, State.OBSERVE)
    await guard.enter(user_id, State.RETRIEVE)
    await guard.enter(user_id, State.PLAN)
    await guard.enter(user_id, State.DECIDE)
    await guard.enter(user_id, State.ACT)
    
    # Relative time
    with patch('scheduler.scheduler.add_job') as mock_add:
        res = await reminder_tool.execute(text="Wake up", time_str="5 minutes", user_id=user_id)
        assert "встановлено" in res
        mock_add.assert_called_once()
    
    # ISO time
    with patch('scheduler.scheduler.add_job') as mock_add:
        future_iso = "2029-01-01 10:00:00"
        res = await reminder_tool.execute(text="Launch", time_str=future_iso, user_id=user_id)
        assert "встановлено" in res
        assert mock_add.called
        # Verify run_date
        _, kwargs = mock_add.call_args
        assert kwargs['run_date'] == datetime.fromisoformat(future_iso)
    
    guard.cleanup_user_lock(user_id)

@pytest.mark.asyncio
async def test_reminder_tool_past_error(reminder_tool):
    from core.state_guard import guard
    from core.state import State
    user_id = 999
    
    await guard.enter(user_id, State.OBSERVE)
    await guard.enter(user_id, State.PLAN)
    await guard.enter(user_id, State.DECIDE)
    await guard.enter(user_id, State.ACT)
    
    res = await reminder_tool.execute(text="Past", time_str="2020-01-01 00:00:00", user_id=user_id)
    assert "future" in res.lower()
    guard.cleanup_user_lock(user_id)

@pytest.mark.asyncio
async def test_stateguard_integration_blocking(note_tool, reminder_tool):
    """
    CRITICAL-TEST: Verify that tools respect StateGuard.
    """
    from core.state_guard import guard
    from core.state import State
    
    user_id = 9999
    
    # 1. Properly reach PLAN state
    await guard.enter(user_id, State.OBSERVE)
    await guard.enter(user_id, State.PLAN)
    
    # 2. Try NoteTool (FS_WRITE) - Forbidden in PLAN
    res_note = await note_tool.execute(action="write", name="hack", content="data", user_id=user_id)
    assert "Security Error" in res_note
    
    # 3. Try ReminderTool (NETWORK) - Forbidden in PLAN
    res_rem = await reminder_tool.execute(text="hack", time_str="1 hour", user_id=user_id)
    assert "Security Error" in res_rem
    
    guard.cleanup_user_lock(user_id)
