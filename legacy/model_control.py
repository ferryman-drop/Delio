"""
Model Control Parameters (MCP)
Adapts model behavior based on user memory

This module derives control parameters from structured memory to:
- Control reasoning depth
- Adjust response length
- Set challenge level
- Optimize for Telegram format (emoji, concise)
"""

import logging
from typing import Dict, Any
import memory_manager_v2 as mm2

logger = logging.getLogger(__name__)

class ModelController:
    """Derives Model Control Parameters from user memory"""
    
    def __init__(self, structured_memory: mm2.StructuredMemory):
        self.memory = structured_memory
    
    def derive_mcp(self, user_id: int) -> Dict[str, Any]:
        """
        Derive Model Control Parameters for a user
        
        Returns:
            {
                'reasoning_depth': 'low' | 'medium' | 'high',
                'response_length': 'short' | 'medium' | 'long',
                'challenge_level': 'soft' | 'adaptive' | 'hard',
                'structure_level': 'bullet' | 'mixed' | 'narrative',
                'platform_format': 'telegram',  # emoji, concise
                'confidence_threshold': 0.5  # min confidence to use memory
            }
        """
        
        # Get all memory with confidence >= 0.5
        all_memory = self.memory.get_all_memory(user_id, min_confidence=0.5)
        
        # Default MCP
        mcp = {
            'reasoning_depth': 'medium',
            'response_length': 'short',  # Default for Telegram
            'challenge_level': 'adaptive',
            'structure_level': 'bullet',  # Telegram-friendly
            'platform_format': 'telegram',
            'use_emoji': True,  # Replace markdown with emoji
            'max_length': 4000,  # Telegram limit
            'confidence_threshold': 0.5
        }
        
        # 1. Reasoning depth (from Life Level)
        life_level_data = all_memory.get('life_level', {})
        current_level = life_level_data.get('current_level', {})
        
        if current_level:
            level_value = current_level.get('value', {})
            if isinstance(level_value, dict):
                level_str = level_value.get('value', 'L3')
            else:
                level_str = level_value
            
            # Extract level number (L1-L7)
            try:
                level_num = int(level_str.replace('L', ''))
                if level_num >= 5:
                    mcp['reasoning_depth'] = 'high'
                elif level_num >= 3:
                    mcp['reasoning_depth'] = 'medium'
                else:
                    mcp['reasoning_depth'] = 'low'
            except:
                pass
        
        # 2. Response length (from feedback signals)
        feedback = all_memory.get('feedback_signals', {})
        verbosity_pref = feedback.get('verbosity_preference', {})
        
        if verbosity_pref:
            pref_value = verbosity_pref.get('value', {})
            if isinstance(pref_value, dict):
                pref_str = pref_value.get('value', 'short')
            else:
                pref_str = pref_value
            
            if pref_str == 'detailed':
                mcp['response_length'] = 'medium'  # Still capped for Telegram
            else:
                mcp['response_length'] = 'short'
        
        # 3. Challenge level (from trust + life level)
        trust_data = all_memory.get('trust_communication', {})
        trust_level = trust_data.get('trust_level', {})
        
        if trust_level:
            trust_value = trust_level.get('value', {})
            if isinstance(trust_value, dict):
                trust_num = trust_value.get('value', 3)
            else:
                trust_num = trust_value if isinstance(trust_value, int) else 3
            
            if trust_num >= 4 and mcp['reasoning_depth'] == 'high':
                mcp['challenge_level'] = 'hard'
            elif trust_num >= 3:
                mcp['challenge_level'] = 'adaptive'
            else:
                mcp['challenge_level'] = 'soft'
        
        # 4. Structure level (from decision patterns)
        decision_data = all_memory.get('decision_patterns', {})
        style = decision_data.get('style', {})
        
        if style:
            style_value = style.get('value', {})
            if isinstance(style_value, dict):
                style_str = style_value.get('value', 'balanced')
            else:
                style_str = style_value
            
            if style_str == 'analytical':
                mcp['structure_level'] = 'mixed'
            elif style_str == 'impulsive':
                mcp['structure_level'] = 'bullet'
            else:
                mcp['structure_level'] = 'bullet'  # Default for Telegram
        
        logger.info(f"🎛️ MCP derived for user {user_id}: depth={mcp['reasoning_depth']}, length={mcp['response_length']}, challenge={mcp['challenge_level']}")
        
        return mcp
    
    def format_for_telegram(self, text: str, mcp: Dict[str, Any]) -> str:
        """
        Format response for Telegram
        - Replace **bold** with emoji bullets
        - Keep concise
        - Use emoji instead of markdown stars
        """
        
        if not mcp.get('use_emoji', True):
            return text
        
        # Simple formatting rules
        # Replace **Header:** with emoji
        text = text.replace('**Life Level:**', '🎯')
        text = text.replace('**Model:**', '🤖')
        text = text.replace('**Reasoning:**', '🧠')
        text = text.replace('**Cost:**', '💰')
        text = text.replace('**Time:**', '⏱')
        
        # Remove excessive markdown
        text = text.replace('**', '')
        
        # Ensure max length
        if len(text) > mcp.get('max_length', 4000):
            text = text[:3900] + "\n\n... (truncated)"
        
        return text


# Global instance
model_controller = None

def init_model_controller(structured_memory: mm2.StructuredMemory):
    """Initialize global model controller"""
    global model_controller
    model_controller = ModelController(structured_memory)
    logger.info("✅ Model Controller initialized")
    return model_controller
