"""
Memory Integration Hook
Integrates advanced memory system into existing core.py

This module provides a wrapper that:
1. Calls existing AI logic
2. Auto-populates memory from interactions
3. Applies MCP formatting for Telegram
"""

import logging
import memory_populator
import model_control

logger = logging.getLogger(__name__)

async def process_with_memory(user_id: int, user_message: str, ai_response: str, 
                              model_used: str, life_level: str = None) -> str:
    """
    Post-process AI interaction:
    1. Auto-populate memory
    2. Apply Telegram formatting
    
    Args:
        user_id: Telegram user ID
        user_message: User's message
        ai_response: AI's response
        model_used: Model that generated response
        life_level: Detected Life Level (from router)
    
    Returns:
        Formatted response for Telegram
    """
    
    try:
        # 1. Auto-populate memory
        if memory_populator.memory_populator:
            memory_populator.memory_populator.process_interaction(
                user_id,
                user_message,
                ai_response,
                model_used,
                life_level
            )
        
        # 2. Get MCP and format for Telegram
        if model_control.model_controller:
            mcp = model_control.model_controller.derive_mcp(user_id)
            formatted_response = model_control.model_controller.format_for_telegram(ai_response, mcp)
            return formatted_response
        
        return ai_response
        
    except Exception as e:
        logger.error(f"Memory integration error: {e}")
        return ai_response  # Fallback to original response
