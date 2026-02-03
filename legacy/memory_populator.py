"""
Memory Auto-Population Engine
Automatically extracts and stores structured memory from conversations

This module analyzes user interactions and populates the 9-section memory:
1. core_identity - Inferred from goals, values, constraints
2. life_level - Calculated from complexity of thinking
3. time_energy - Detected from complaints about time/focus
4. skills_map - Mentioned skills and expertise
5. money_model - Income discussions, financial pressure
6. goals - Explicitly stated or implied goals
7. decision_patterns - How user approaches decisions
8. behavior_discipline - Follow-through on commitments
9. trust_communication - Preferred communication style
10. feedback_signals - Reactions to advice
"""

import logging
import json
from typing import Dict, Any, Optional
import memory_manager_v2 as mm2

logger = logging.getLogger(__name__)

class MemoryPopulator:
    """Automatically populates structured memory from conversations"""
    
    def __init__(self, structured_memory: mm2.StructuredMemory):
        self.memory = structured_memory
        self.confidence_engine = mm2.ConfidenceEngine(structured_memory)
    
    def process_interaction(self, user_id: int, user_message: str, ai_response: str, 
                           model_used: str, life_level: Optional[str] = None):
        """Process a single interaction and update memory"""
        
        # 1. Update Life Level (from Router)
        if life_level:
            self._update_life_level(user_id, life_level)
        
        # 2. Extract goals
        self._extract_goals(user_id, user_message)
        
        # 3. Detect decision patterns
        self._detect_decision_patterns(user_id, user_message)
        
        # 4. Update feedback signals
        self._update_feedback(user_id, user_message, ai_response, model_used)
        
        # 5. Detect time/energy signals
        self._detect_time_energy(user_id, user_message)
        
        # 6. Extract skills mentions
        self._extract_skills(user_id, user_message)
    
    def _update_life_level(self, user_id: int, life_level: str):
        """Update Life Level with confidence scoring"""
        existing = self.memory.get_memory(user_id, 'life_level', 'current_level')
        
        if existing:
            existing_level = existing['value'].get('value') if isinstance(existing['value'], dict) else existing['value']
            if existing_level == life_level:
                # Same level - increase confidence
                self.memory.update_confidence(user_id, 'life_level', 'current_level', +0.05)
            else:
                # Different level - gradual transition
                self.memory.set_memory(user_id, 'life_level', 'previous_level', existing_level, mm2.HIGH_CONFIDENCE)
                self.memory.set_memory(user_id, 'life_level', 'current_level', life_level, mm2.DEFAULT_CONFIDENCE)
        else:
            # First time
            self.memory.set_memory(user_id, 'life_level', 'current_level', life_level, mm2.DEFAULT_CONFIDENCE)
    
    def _extract_goals(self, user_id: int, message: str):
        """Extract goals from user message (simple keyword detection)"""
        goal_keywords = ['хочу', 'планую', 'мета', 'ціль', 'досягти', 'зробити', 'створити']
        
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in goal_keywords):
            # Simple extraction - in production, use LLM
            self.memory.set_memory(
                user_id,
                'goals',
                'mentioned_goals',
                {'raw_text': message[:200], 'detected_at': mm2.datetime.now().isoformat()},
                mm2.LOW_CONFIDENCE,
                metadata={'source': 'keyword_detection'}
            )
            logger.info(f"🎯 Goal signal detected for user {user_id}")
    
    def _detect_decision_patterns(self, user_id: int, message: str):
        """Detect decision-making patterns"""
        # Impulsive indicators
        impulsive_keywords = ['зараз', 'швидко', 'негайно', 'одразу']
        # Analytical indicators
        analytical_keywords = ['аналіз', 'порівняти', 'подумати', 'розглянути']
        
        message_lower = message.lower()
        
        if any(kw in message_lower for kw in impulsive_keywords):
            self.confidence_engine.confirm_signal(user_id, 'decision_patterns', 'style', 'impulsive')
        elif any(kw in message_lower for kw in analytical_keywords):
            self.confidence_engine.confirm_signal(user_id, 'decision_patterns', 'style', 'analytical')
    
    def _update_feedback(self, user_id: int, user_message: str, ai_response: str, model_used: str):
        """Track what kind of responses work"""
        # Simple heuristic: short messages = prefer concise responses
        if len(user_message) < 50:
            self.confidence_engine.confirm_signal(user_id, 'feedback_signals', 'verbosity_preference', 'short')
        elif len(user_message) > 200:
            self.confidence_engine.confirm_signal(user_id, 'feedback_signals', 'verbosity_preference', 'detailed')
    
    def _detect_time_energy(self, user_id: int, message: str):
        """Detect time pressure and energy state"""
        overload_keywords = ['немає часу', 'перевантажений', 'багато справ', 'не встигаю']
        
        message_lower = message.lower()
        
        if any(kw in message_lower for kw in overload_keywords):
            self.memory.set_memory(
                user_id,
                'time_energy',
                'energy_state',
                'overloaded',
                mm2.DEFAULT_CONFIDENCE
            )
            logger.info(f"⚡ Time pressure detected for user {user_id}")
    
    def _extract_skills(self, user_id: int, message: str):
        """Extract mentioned skills"""
        # Common skill keywords
        tech_skills = ['python', 'javascript', 'react', 'docker', 'kubernetes', 'ai', 'ml']
        
        message_lower = message.lower()
        
        for skill in tech_skills:
            if skill in message_lower:
                existing_skills = self.memory.get_memory(user_id, 'skills_map', 'hard_skills')
                
                if existing_skills:
                    skills_list = existing_skills['value'].get('value', [])
                    if skill not in skills_list:
                        skills_list.append(skill)
                        self.memory.set_memory(user_id, 'skills_map', 'hard_skills', skills_list, mm2.DEFAULT_CONFIDENCE)
                else:
                    self.memory.set_memory(user_id, 'skills_map', 'hard_skills', [skill], mm2.DEFAULT_CONFIDENCE)
                
                logger.info(f"🛠️ Skill detected: {skill} for user {user_id}")


# Global instance
memory_populator = None

def init_memory_populator(structured_memory: mm2.StructuredMemory):
    """Initialize global memory populator"""
    global memory_populator
    memory_populator = MemoryPopulator(structured_memory)
    logger.info("✅ Memory Auto-Populator initialized")
    return memory_populator
