import logging
import asyncio
import config
import json
import re
from typing import List, Dict, Any
from states.base import BaseState
from core.state import State
from core.context import ExecutionContext
from core import llm_service
from core.tool_registry import registry

logger = logging.getLogger("Delio.Plan")

class PlanState(BaseState):
    async def execute(self, context: ExecutionContext) -> State:
        logger.debug(f"🤔 Planning for user {context.user_id} (Actor-Critic Mode)")
        
        try:
            # 1. Build context-aware system instruction
            system_instruction = self._build_system_instruction(context)
            
            # 2. ACTOR PHASE (Gemini)
            preferred = context.metadata.get("preferred_model", "gemini")
            
            # Use new service adapter
            resp_text, model_used = await llm_service.call_actor(
                user_id=context.user_id,
                text=context.raw_input,
                system_instruction=system_instruction,
                preferred_model=preferred,
                image_path=context.metadata.get("image_path")
            )
            
            # 3. CRITIC PHASE (DeepSeek validation)
            if config.ENABLE_SYNERGY and "Error" not in model_used:
                validated_resp, synergy_label = await llm_service.call_critic(
                    user_query=context.raw_input,
                    actor_response=resp_text,
                    instruction=system_instruction
                )
                
                final_text = validated_resp
                context.metadata["model_used"] = synergy_label
            else:
                final_text = resp_text
                # Icon mapping
                icon = "♊"
                if "pro" in model_used.lower(): icon = "🎓"
                elif "deepseek" in model_used.lower(): icon = "🐋"
                context.metadata["model_used"] = icon

            # 4. PARSE TOOL CALLS (JSON Extraction)
            # --- ROBUST JSON PARSER (Fix for "Regex Trap") ---
            try:
                # Find the first '{' and last '}'
                start_idx = final_text.find('{')
                end_idx = final_text.rfind('}')
                
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_str = final_text[start_idx:end_idx+1]
                    # Sanitize common LLM mistakes (like trailing commas)
                    # For now, rely on stdlib, but could upgrade to json_repair
                    data = json.loads(json_str)
                    
                    if "tool_calls" in data:
                        context.tool_calls = data["tool_calls"]
                    else:
                        context.tool_calls = [] # Valid JSON but no tool calls
                else:
                    context.tool_calls = [] # No JSON found
                    
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ JSON Parse Error: {e}. Raw text: {final_text[:100]}...")
                context.tool_calls = [] # Fallback to text-only
            
            # Clean response text from JSON for display (optional, depending on UX)
            context.response = self._cleanup_response(final_text)

            # 5. Telemetry
            try:
                import telemetry
                telemetry.log_routing_event(
                    user_id=context.user_id,
                    life_level=context.metadata.get("life_level", "Unknown"),
                    complexity="Medium", 
                    model=context.metadata["model_used"],
                    in_txt=context.raw_input,
                    out_txt=context.response
                )
            except Exception as te:
                logger.warning(f"⚠️ Telemetry fail: {te}")
            
            # --- CONDITIONAL ROUTING ---
            
            # 1. Check for Critic Rejection
            synergy_label = context.metadata.get("model_used", "")
            # Route to ERROR only if it's a REAL rejection/error, NOT a simple API timeout
            if "⚠️" in synergy_label and "(Timeout)" not in synergy_label:
                logger.warning(f"⛔ Plan Rejected by Critic. User: {context.user_id}")
                context.errors.append("Critic rejected the response (Potential Safety/Logic Issue)")
                return State.ERROR
            
            # 2. Check for Empty Response (if no tool calls)
            if not context.tool_calls and (not context.response or len(context.response.strip()) < 2):
                logger.warning(f"⛔ Plan Empty. User: {context.user_id}")
                context.errors.append("Actor produced empty response")
                return State.ERROR

            return State.DECIDE
            
        except Exception as e:
            logger.exception(f"❌ Error in PlanState: {e}")
            context.errors.append(str(e))
            return State.ERROR

    def _build_system_instruction(self, context: ExecutionContext) -> str:
        # (Same as before, keep consolidated)
        mem = context.memory_context
        instruction_parts = [
            f"Ти — {config.yaml_config.get('bot', {}).get('name', 'Delio')}, персональний AI-асистент (AID).",
            "Ти працюєш згідно зі своєю конституцією (FSM State Machine).\n",
            "### ВАШ ПРОФІЛЬ ТА КОНТЕКСТ ЖИТТЯ:"
        ]
        
        structured = mem.get("structured_profile", {})
        for section, items in structured.items():
            if items:
                items_str = ", ".join([f"{k}: {v.get('value')}" for k, v in items.items()])
                instruction_parts.append(f"• **{section.title()}**: {items_str}")
        
        memories = mem.get("long_term_memories", [])
        if memories:
            instruction_parts.append("\n### ВАЖЛИВІ ФАКТИ З МИНУЛИХ РОЗМОВ:")
            for m in memories:
                instruction_parts.append(f"• {m}")

        # --- TOOL DEFINITIONS ---
        tools = registry.get_definitions()
        if tools:
            instruction_parts.append("\n### ДОСТУПНІ ІНСТРУМЕНТИ (TOOLS):")
            instruction_parts.append("Якщо тобі потрібно виконати дію, виклич інструмент, повернувши JSON у форматі:")
            instruction_parts.append("```json\n{\"tool_calls\": [{\"name\": \"tool_name\", \"arguments\": {\"arg1\": \"val1\"}}]}\n```")
            for t in tools:
                instruction_parts.append(f"- **{t['name']}**: {t['description']}")
                instruction_parts.append(f"  Params: {json.dumps(t['parameters'])}")

        # --- TOOL OUTPUTS (If returning from ACT) ---
        if context.tool_outputs:
            instruction_parts.append("\n### РЕЗУЛЬТАТИ ВИКОНАННЯ ІНСТРУМЕНТІВ:")
            for output in context.tool_outputs:
                name = output.get("name")
                res = output.get("output") or output.get("error")
                instruction_parts.append(f"• Tool '{name}': {res}")
            
            # Important: Clear tool_outputs or track them to avoid infinite reprocessing if not careful
            # Generally, we want to clear tool_calls so we don't re-execute them
            context.tool_calls = []

        # --- IMAGE CONTEXT ---
        if context.metadata.get("image_path"):
            instruction_parts.append("\n### [СИГНАЛ: ЗОБРАЖЕННЯ]")
            instruction_parts.append("Користувач надіслав зображення. Аналізуй його першочергово та надай детальну відповідь на основі візуальних даних.")
            instruction_parts.append("ФОРМАТ ВІДПОВІДІ (ОБОВ'ЯЗКОВО розділяй подвійним переносом рядка):")
            instruction_parts.append("1. [Короткий візуальний опис]")
            instruction_parts.append("\n\n2. [Твоя інтерпретація, філософський зв'язок або імпровізація]")
            instruction_parts.append("\n\n3. [Заклик до дії або стратегічна порада]")
            
            if context.raw_input and "[IMAGE UPLOAD]" in context.raw_input:
                # If it's a raw upload without specific question beyond caption
                instruction_parts.append("Мета користувача: Дізнатись, що на фото та почути твою думку.")

        # --- HEARTBEAT CONTEXT ---
        if context.event_type == "heartbeat":
            instruction_parts.append("\n### [СИГНАЛ: HEARTBEAT CHECK-IN]")
            instruction_parts.append("Цей запит ініційовано автоматично (Proactive Heartbeat). Твоя задача — перевірити контекст користувача (цілі, час, нагадування).")
            instruction_parts.append("1. Якщо є щось КРИТИЧНО ВАЖЛИВЕ або КОРИСНЕ (нагадування, мотивація, питання по цілі) — напиши це.")
            instruction_parts.append("2. Якщо нічого важливого немає — просто виведи слово 'SKIP'.")
            instruction_parts.append("3. НЕ вітайся, якщо в цьому немає потреби. НЕ пиши 'Як справи?', якщо немає контексту.")
            instruction_parts.append("Bias towards SILENCE (SKIP). Speak only when valuable.")

        instruction_parts.append("\n### ТВОЇ ОСНОВНІ ІНСТРУКЦІЇ:")

        # --- ACTIVE REFLECTION (Task-012) ---
        try:
            import sqlite3
            conn = sqlite3.connect('/root/ai_assistant/data/bot_data.db')
            cursor = conn.cursor()
            cursor.execute("""
                SELECT critique, correction FROM lessons_learned 
                WHERE user_id = ? AND score < 7 
                ORDER BY created_at DESC LIMIT 3
            """, (context.user_id,))
            lessons = cursor.fetchall()
            conn.close()
            
            if lessons:
                instruction_parts.append("\n### ⚠️ CRITICAL LEARNINGS FROM PAST MISTAKES:")
                for idx, (critique, correction) in enumerate(lessons):
                    instruction_parts.append(f"{idx+1}. Issue: {critique} -> Fix: {correction}")
                instruction_parts.append("DO NOT REPEAT THESE ERRORS.")
        except Exception:
            pass # Fail silently
        instruction_parts.append(config.SYSTEM_PROMPT)
        instruction_parts.append("\n" + config.TELEGRAM_STYLE)
        
        return "\n".join(instruction_parts)

    def _extract_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """Extracts tool calls from JSON blocks in the text."""
        try:
            # Look for JSON blocks
            json_blocks = re.findall(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if not json_blocks:
                # Try simple brace matching if no markdown blocks
                match = re.search(r"(\{.*\})", text, re.DOTALL)
                if match:
                    json_blocks = [match.group(1)]
            
            tool_calls = []
            for block in json_blocks:
                try:
                    data = json.loads(block)
                    if "tool_calls" in data:
                        tool_calls.extend(data["tool_calls"])
                except json.JSONDecodeError:
                    continue
            return tool_calls
        except Exception as e:
            logger.error(f"Error parsing tool calls: {e}")
            return []

    def _cleanup_response(self, text: str) -> str:
        """Removes JSON blocks from the response for cleaner output."""
        clean = re.sub(r"```json\s*(.*?)\s*```", "", text, flags=re.DOTALL).strip()
        # If it was just JSON, return a placeholder or empty
        return clean
