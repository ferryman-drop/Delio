import logging
import redis
import json
from datetime import datetime
import config
import memory_manager_v2 as mm2

logger = logging.getLogger(__name__)

# Redis Client
r = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True)

# State Constants
STATE_IDLE = "IDLE"
STATE_ASKING = "ASKING"

# Sections to prioritize
PRIORITY_SECTIONS = [
    "core_identity",
    "goals", 
    "skills_map",
    "life_level",
    "principles",
    "money_model",
    "time_energy",
    "behavior_discipline",
    "trust_communication",
    "feedback_signals"
]

class Interviewer:
    def __init__(self):
        self.mm = mm2.structured_memory # Assumed initialized
    
    def is_active(self, user_id: int) -> bool:
        """Check if user is in an interview"""
        state = r.get(f"interview:state:{user_id}")
        return state == STATE_ASKING

    async def start_interview(self, user_id: int):
        """Start the interview process: Pick a missing section"""
        if not self.mm:
            self.mm = mm2.init_structured_memory(config.DB_PATH)
            
        # 1. Analyze Memory
        mem = self.mm.get_all_memory(user_id)
        target_section = None
        
        for sec in PRIORITY_SECTIONS:
            # Check if recently skipped
            if r.exists(f"interview:skip:{user_id}:{sec}"):
                continue

            # Check if section exists and has meaningful data
            if sec not in mem or not mem[sec]:
                target_section = sec
                break
            
            # Additional check: Is it just an initialized placeholder?
            if len(mem[sec]) == 0:
                target_section = sec
                break
        
        if not target_section:
            # If all skipped or full, try clearing skips? Or just say done.
            # Let's check if we have any skipped ones to fallback
            if any(r.exists(f"interview:skip:{user_id}:{s}") for s in PRIORITY_SECTIONS):
                return "😴 **Відкладено.** Ви пропустили всі доступні питання. Спробуйте пізніше (через годину)."
            
            return "🎉 **Все добре!** Ваша пам'ять заповнена. Я не бачу критичних прогалин. Використовуйте `/memory`, щоб переглянути."

        # 2. Generate Question
        question = self._generate_question(target_section)
        
        # 3. Set State
        r.set(f"interview:state:{user_id}", STATE_ASKING)
        r.set(f"interview:section:{user_id}", target_section)
        
        return f"🎤 **Режим Інтерв'ю**\nДавайте заповнимо розділ **{str(target_section).replace('_', ' ').title()}**.\n\n{question}\n\n(Напишіть відповідь, або /cancel щоб скасувати, /skip щоб пропустити)"

    async def process_answer(self, user_id: int, text: str):
        """Handle user answer during interview"""
        if text.strip().lower() in ["/cancel", "/skip", "пропустити", "далі", "next"]:
            # Mark section as skipped for 1 hour
            section = r.get(f"interview:section:{user_id}")
            if section:
                r.setex(f"interview:skip:{user_id}:{section}", 3600, "1")
            
            self._clear_state(user_id)
            return f"🚫 Питання про **{section}** відкладено на 1 годину."
        
        section = r.get(f"interview:section:{user_id}")
        if not section:
            self._clear_state(user_id)
            return "⚠️ Помилка: Втрачено стан інтерв'ю."
            
        # 1. Analyze & Save Answer
        key = f"reported_{datetime.now().strftime('%H%M')}"
        if section == "goals": key = "primary_goal"
        elif section == "core_identity": key = "self_description"
        elif section == "skills_map": key = "top_skills"
        
        self.mm.set_memory(
            user_id, 
            section, 
            key, 
            text, 
            confidence=0.8, 
            metadata={"source": "interview"}
        )
        
        # 2. Clear state
        self._clear_state(user_id)
        
        return f"✅ Збережено! Оновлено розділ {section}.\n\nЯ додав це у пам'ять. Напишіть /interview знову, щоб продовжити заповнювати прогалини."

    def _generate_question(self, section: str) -> str:
        """Generate a contextual question for the section"""
        prompts = {
            "core_identity": "Хто ви є (окрім вашої професії)? Які ваші ключові цінності?",
            "goals": "Яка ваша головна ціль #1 на найближчі 3 місяці?",
            "skills_map": "Які ваші топ-3 професійні навички (Hard Skills)?",
            "life_level": "Як би ви оцінили свій поточний Рівень Життя? (Виживання, Стабільність, Зростання або Стратегія?)",
            "principles": "Яким одним головним принципом ви керуєтесь у житті?",
            "money_model": "Яка ваша фінансова стратегія на цей рік? (Накопичення, Інвестиції, Виживання?)",
            "time_energy": "Коли у вас пік продуктивності протягом дня? (Ранок, Ніч?)",
            "behavior_discipline": "Яку одну звичку ви хочете виробити найближчим часом?",
            "trust_communication": "Який стиль спілкування вам найбільше підходить? (Прямий, М'який, Детальний?)",
            "feedback_signals": "Що вас найбільше мотивує в роботі? (Результат, Процес, Визнання?)"
        }
        return prompts.get(section, f"Розкажіть мені про {section.replace('_', ' ')}.")

    def _clear_state(self, user_id: int):
        r.delete(f"interview:state:{user_id}")
        r.delete(f"interview:section:{user_id}")

# Global Instance
interviewer_instance = Interviewer()
