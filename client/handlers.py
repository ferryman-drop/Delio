from aiogram import Router, types
from aiogram.filters import Command
import httpx
import logging

router = Router()
logger = logging.getLogger("Delio.Client")
API_URL = "http://localhost:8000/v1/chat"

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 Delio v4.0 Client Online. Підключаюсь до ядра...")
    # Send initial handshake?
    await handle_any_message(message)

@router.message()
async def handle_any_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text or ""
    
    # Visual Feedback (Optimistic UI)
    status_msg = await message.answer("🤔 ...")
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(API_URL, json={
                "user_id": user_id,
                "message": text,
                "message_id": status_msg.message_id,
                "platform": "telegram"
            }, timeout=120.0) # Long timeout for FSM
            
            if resp.status_code == 200:
                # The response has already been sent to the user via RespondState in chunks.
                # No need to edit again here.
                pass
            else:
                await status_msg.edit_text(f"⚠️ Kernel Error: {resp.status_code}\n{resp.text}")

    except Exception as e:
        logger.error(f"Client Bridge Error: {e}")
        await status_msg.edit_text(f"⚠️ **Connection Lost:** {str(e)}")
