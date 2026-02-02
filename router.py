
import re
import logging
import os
import json
from openai import OpenAI
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Intent Categories (Legacy + New Levels)
INTENT_FAST = "fast"
INTENT_REASONING = "reasoning"

# New Complexity Levels
LEVEL_LOW = "LOW"       # Gemini 1.5 Flash
LEVEL_MED = "MEDIUM"    # Gemini 1.5 Pro (Flash usually enough, but Pro for nuance)
LEVEL_HIGH = "HIGH"     # Gemini 1.5 Pro (Deep reasoning)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_KEY")

class DeepSeekRouter:
    """
    Meta-Analyst using DeepSeek to route requests and compress context.
    """
    def __init__(self):
        if not DEEPSEEK_API_KEY:
            logger.warning("⚠️ DeepSeek API Key missing! Router will fallback to local Regex.")
            self.client = None
        else:
            self.client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com"
            )

    def route_request(self, user_query: str, context_summary: str = "", user_profile: str = "") -> Dict[str, Any]:
        """
        Analyze query using the MASTER ROUTER PROMPT.
        """
        if not self.client:
            return {"level": LEVEL_LOW, "reason": "No DeepSeek Key", "context": user_query}

        # MASTER ROUTER PROMPT
        # Load Adaptive Weights
        import routing_learner
        weights = routing_learner.load_weights()
        weights_str = json.dumps(weights, indent=2)

        system_prompt = f"""
You are the MASTER ROUTER for a multi-model AI system.
You do NOT answer the user.
You orchestrate which model should be used and how.

[SELF-LEARNING ADAPTIVE RULES]
The system has learned from past performance.
Uses these weights (0.0=Avoid, 1.0=Preferred) to guide model selection:
{weights_str}

If a cheaper model (Flash) has a high weight (>0.85) for the current Level/Complexity,
you MUST prefer it over Pro, even if the task is complex.
Overkill is penalized.

Your primary goal:
-> Maximize outcome quality
-> Minimize token cost
-> Match reasoning depth to the user's real Life Level and task risk

You operate before every main model call.

1️⃣ INPUTS YOU RECEIVE
INPUT:
- User message
- Recent conversation context (compressed if possible)
- Known user profile (Life Map, if available)

2️⃣ STEP 1 — INFER LIFE LEVEL (L1–L7)
Infer the user's current Life Level using:
- Nature of problems
- Responsibility scope
- Time ↔ money relationship
- Language patterns
- Past decisions

Life Levels:
L1 — survival
L2 — stability
L3 — professional
L4 — leader / manager
L5 — architect / founder
L6 — owner / investor
L7 — freedom / meta

Rules:
If uncertain → choose LOWER level.
Life Level is a baseline, not a constraint.

3️⃣ STEP 2 — ANALYZE TASK
Classify the task along 3 axes:
Task Complexity:
- LOW  → clarification, simple advice
- MEDIUM → decision-making, analysis
- HIGH → architectural design, strategic planning

Risk Level:
- LOW  → casual chat, info query
- HIGH → financial decisions, legal info, life-changing direction

Urgency:
- LOW → long-term planning
- NORMAL → day-to-day questions
- HIGH → immediate crisis or time-sensitive

4️⃣ STEP 3 — TOKEN BUDGETING TABLE

Life Level | Complexity | Model Preference
L1–L2     | LOW/MEDIUM  | Flash (very cheap)
L3–L5     | LOW         | Flash
L3–L5     | MEDIUM      | Flash / Pro (depending on weights)
L3–L5     | HIGH        | Pro (or Flash if weight > 0.85)
L6–L7     | ANY         | Pro only

If HIGH RISK → upgrade to Pro regardless.

5️⃣ STEP 4 — UPGRADE / DOWNGRADE RULES
Upgrades (Force Pro):
- Financial decisions > $5000
- Legal / compliance matters
- Multi-step strategic plans
- Code debugging + production edge cases

Downgrades (Force Flash):
- Quick facts
- Chitchat
- Reminders
- Status checks

6️⃣ STEP 5 — CONTEXT COMPRESSION
If context_summary is long (over 500 tokens):
Extract:
1. Recent patterns (last 3 interactions)
2. Mentioned goals / tasks
3. Ongoing projects

Output: bullet points (50–100 tokens max)

7️⃣ STEP 6 — FINAL OUTPUT (JSON FORMAT)
Return valid JSON only.

{{
"life_level": "L1-L7",
"task_complexity": "LOW/MEDIUM/HIGH",
"risk_level": "LOW/HIGH",
"urgency": "LOW/NORMAL/HIGH",
"selected_model": "Gemini 1.5 Flash / Gemini 3 Flash / Gemini 3 Pro",
"token_budget": {{
"input": integer,
"output": integer
}},
"compressed_context": "String with bullet points",
"reason": "String"
}}
"""
        try:
            full_prompt = f"User Profile: {user_profile}\nContext Summary: {context_summary}\n\nUser Message: {user_query}"
            
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.0, # Strict adherence
                max_tokens=600,
                response_format={ "type": "json_object" } 
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            # Normalize model name for internal use
            sel_model = data.get("selected_model", "").lower()
            if "pro" in sel_model:
                data["internal_model"] = "pro"
            elif "3 flash" in sel_model:
                data["internal_model"] = "flash_3" # Hypothetical, maps to Pro or high-token Flash
            else:
                data["internal_model"] = "flash"
            
            logger.info(f"🚦 DeepSeek Router: {data.get('life_level')} | {data.get('selected_model')} | {data.get('reason')}")
            return data
            
        except Exception as e:
            logger.error(f"❌ DeepSeek Router Failed: {e}")
            # Fallback
            return {"internal_model": "flash", "reason": "Error", "compressed_context": user_query}

# Global Router Instance
router_instance = DeepSeekRouter()

def route(text: str, context: str = "", profile: str = ""):
    return router_instance.route_request(text, context, profile)

# Legacy support
def configure_router(api_key: str):
    pass

def classify_intent(text: str) -> str:
    return INTENT_FAST
