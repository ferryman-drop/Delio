import logging
from core.tool_registry import BaseTool, ToolDefinition, registry
from core.memory.writer import writer

logger = logging.getLogger("Delio.ProfileTool")

class ProfileTool(BaseTool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="update_profile",
            description="Update the user's structured profile (Life OS Dimensions). Use this to store permanent facts, goals, or life level changes.",
            parameters={
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "enum": [
                            "core_identity", "life_level", "time_energy", 
                            "skills_map", "money_model", "goals", 
                            "decision_patterns", "behavior_discipline", 
                            "trust_communication", "feedback_signals"
                        ],
                        "description": "Specific dimension of the user's life."
                    },
                    "key": {
                        "type": "string",
                        "description": "The attribute key (e.g. 'name', 'current_job', 'primary_goal')."
                    },
                    "value": {
                        "type": "string",
                        "description": "The value to store."
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Level of certainty (0.1 to 1.0). Default: 0.8",
                        "default": 0.8
                    }
                },
                "required": ["section", "key", "value"]
            },
            requires_confirmation=False
        )

    async def execute(self, **kwargs) -> str:
        user_id = kwargs.get("user_id")
        section = kwargs.get("section")
        key = kwargs.get("key")
        value = kwargs.get("value")
        confidence = kwargs.get("confidence", 0.8)

        if not user_id:
            return "❌ Error: user_id missing."

        try:
            # We bypass the limited update_attribute and call structured directly for flexibility
            await writer.structured.set_memory(
                user_id=user_id,
                section=section,
                key=key,
                value=value,
                confidence=float(confidence)
            )
            logger.info(f"💾 Profile Updated: {section}.{key} = {value} (User: {user_id})")
            return f"✅ Profile updated: {section} -> {key} is now set."
        except Exception as e:
            logger.error(f"Profile tool failure: {e}")
            return f"❌ Failed to update profile: {str(e)}"

# Register
registry.register(ProfileTool())
