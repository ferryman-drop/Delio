import logging
import config
from core.life_cycle import AgeService

logger = logging.getLogger("Delio.Personality")

class PersonalityEngine:
    @staticmethod
    def get_system_instructions() -> str:
        """
        Constructs the System Prompt by combining the Base Persona 
        with Dynamic Life Stage traits.
        """
        base_prompt = config.SYSTEM_PROMPT
        
        # 1. Get Life Stage
        stage_info = AgeService.get_life_stage(config.persona_config)
        
        # 2. Inject Dynamic Context
        stage_name = stage_info.get("name", "Unknown").upper()
        age_days = stage_info.get("age", 0)
        traits = stage_info.get("data", {}).get("traits", "Neutral")
        verbosity = stage_info.get("data", {}).get("verbosity", "Normal")
        
        dynamic_context = f"""
### [DYNAMIC PERSONA: ACTIVE]
• **System Age**: {age_days} days.
• **Life Stage**: {stage_name}.
• **Traits**: {traits}.
• **Verbosity Mode**: {verbosity}.

INSTRUCTION: Adapt your tone to match this Life Stage. 
If INFANT/CHILD: Be curious, ask questions, be enthusiastic.
If ADOLESCENT: Be confident, challenge assumptions.
If ADULT: Be concise, expert, strategic.
"""
        # Append to the base prompt
        full_prompt = f"{base_prompt}\n{dynamic_context}"
        
        # logger.debug(f"🧬 Persona generated for Stage: {stage_name}")
        return full_prompt

