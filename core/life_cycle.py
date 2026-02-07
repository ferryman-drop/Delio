from datetime import datetime
import logging
import yaml
import config

logger = logging.getLogger("Delio.LifeCycle")

class AgeService:
    @staticmethod
    def get_birth_date() -> datetime:
        return datetime.fromisoformat(config.BIRTH_TIMESTAMP)

    @staticmethod
    def get_age_days() -> int:
        delta = datetime.now() - AgeService.get_birth_date()
        return max(0, delta.days)

    @staticmethod
    def get_life_stage(persona_config: dict) -> dict:
        """
        Determines the current life stage based on age and persona.yaml config.
        """
        age = AgeService.get_age_days()
        stages = persona_config.get("life_stages", {})
        
        # Determine stage by max_days definition
        # Default order: Infant -> Child -> Adolescent -> Adult
        # We assume yaml is unordered, so let's resort or check logic.
        
        # Simple logic: find first stage where age < max_days
        # But we need them sorted by max_days to work.
        
        sorted_stages = sorted(stages.items(), key=lambda x: x[1].get("max_days", 9999))
        
        for stage_name, data in sorted_stages:
            max_days = data.get("max_days", 9999)
            if age <= max_days:
                return {
                    "name": stage_name, 
                    "age": age,
                    "data": data
                }
        
        # Fallback to last one (Adult)
        if sorted_stages:
            last = sorted_stages[-1]
            return {"name": last[0], "age": age, "data": last[1]}
            
        return {"name": "Unknown", "age": age, "data": {}}

