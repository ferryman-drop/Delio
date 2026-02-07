import os
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
import logging
import config
from core.api_models import ChatRequest, ChatResponse
from core.engine import process_request, init_engine
from core.fsm import instance as fsm

from aiogram import Bot

# Setup Logging
logger = logging.getLogger("Delio.Server")

# API Key Authentication
API_KEY = os.getenv("DELIO_API_KEY", "")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    if not API_KEY:
        return  # No key configured = open (dev mode)
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

app = FastAPI(
    title="Delio AI Kernel",
    version="4.0.0",
    description="Headless AI Kernel with FSM Architecture"
)

# Real Bot for Out-of-band notifications (Corrections)
real_bot = Bot(token=config.TG_TOKEN)

@app.on_event("startup")
async def startup_event():
    logger.info("📡 Starting Delio Headless Server...")
    try:
        init_engine(real_bot=real_bot)
        # CRASH AMNESIA: Reset states
        await fsm.force_reset_all_users()
        logger.info("✅ Engine Initialized successfully")
    except Exception as e:
        logger.critical(f"❌ Failed to initialize engine: {e}")
        raise e

@app.get("/health")
async def health_check():
    return {
        "status": "ok", 
        "version": "4.0.0-Headless",
        "service": "Delio Kernel"
    }

@app.post("/v1/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat_endpoint(request: ChatRequest):
    try:
        context = await process_request(
            user_id=request.user_id,
            text=request.message,
            message_id=request.message_id,
            platform=request.platform
        )
        
        # Determine Status
        status = "complete"
        msg = context.sent_response
        
        # Fallback Logic
        if not msg:
            if context.errors:
                msg = f"⚠️ Error: {context.errors}"
                status = "error"
            else:
                msg = context.response or "⚠️ No response."
                status = "processing" if not context.response else "complete"

        # Model used
        model_used = context.metadata.get("model_used", "Delio-FSM")

        return ChatResponse(
            text=msg,
            model_used=model_used,
            tool_calls=context.tool_calls,
            lifecycle_status=status
        )
        
    except Exception as e:
        logger.error(f"❌ API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "server:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True
    )
