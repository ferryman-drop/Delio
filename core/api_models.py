from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class ChatRequest(BaseModel):
    user_id: int
    message: str
    message_id: Optional[int] = None # For optimistic corrections
    platform: str = "telegram"
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ChatResponse(BaseModel):
    text: str
    model_used: str
    tool_calls: Optional[list] = None
    lifecycle_status: str = "complete" # complete, processing, error
