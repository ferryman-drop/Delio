import logging
import config
import asyncio
from states.base import BaseState
from core.state import State
from core.context import ExecutionContext

logger = logging.getLogger("Delio.Plan")

class PlanState(BaseState):
    async def execute(self, context: ExecutionContext) -> State:
        logger.debug(f"🤔 Planning for user {context.user_id} (Actor-Critic Mode)")
        
        try:
            # 1. Build context-aware system instruction
            system_instruction = self._build_system_instruction(context)
            
            # 2. ACTOR PHASE (Gemini)
            import old_core as legacy_core
            preferred = context.metadata.get("preferred_model", "gemini")
            
            # We call the legacy actor
            resp_text, model_used = await legacy_core.call_llm_agentic(
                user_id=context.user_id,
                text=context.raw_input,
                system_prompt=system_instruction,
                preferred=preferred
            )
            
            # 3. CRITIC PHASE (DeepSeek validation)
            if config.ENABLE_SYNERGY and "Error" not in model_used:
                validated_resp, synergy_label = await self._run_critic(
                    user_query=context.raw_input,
                    actor_response=resp_text,
                    instruction=system_instruction
                )
                
                context.response = validated_resp
                context.metadata["model_used"] = synergy_label
            else:
                context.response = resp_text
                # Icon mapping
                icon = "♊"
                if "pro" in model_used.lower(): icon = "🎓"
                elif "deepseek" in model_used.lower(): icon = "🐋"
                context.metadata["model_used"] = icon

            # 4. Telemetry (Log for /logic command)
            try:
                import telemetry
                telemetry.log_routing_event(
                    user_id=context.user_id,
                    life_level=context.metadata.get("life_level", "Unknown"),
                    complexity="Medium", # Static for now, can be dynamic
                    model=context.metadata["model_used"],
                    in_txt=context.raw_input,
                    out_txt=context.response
                )
            except Exception as te:
                logger.warning(f"⚠️ Telemetry fail: {te}")
            
            return State.DECIDE
            
        except Exception as e:
            logger.exception(f"❌ Error in PlanState: {e}")
            context.errors.append(str(e))
            return State.ERROR

    async def _run_critic(self, user_query, actor_response, instruction) -> (str, str):
        """
        Actor-Critic Synergy: DeepSeek validates the Actor's (Gemini) response.
        """
        try:
            from openai import OpenAI
            ds_client = OpenAI(api_key=config.DEEPSEEK_KEY, base_url="https://api.deepseek.com")
            
            synergy_prompt = f"""[ACTOR-CRITIC SYNERGY] 
Ти — AID Critic (DeepSeek). Твоя задача — проаналізувати відповідь AID Actor (Gemini).

ПРАВИЛА:
1. Якщо відповідь правильна, логічна та безпечна — поверни статус: "✅ VALIDATED" і саму відповідь без затримок.
2. Якщо є помилки, логічні прогалини або відхилення від інструкцій — надай ТІЛЬКИ покращену версію відповіді.
3. Звертай увагу на точність фактів та відповідність Life Level користувача.

ІНСТРУКЦІЯ АКТОРУ:
{instruction[:500]}... (truncated)

{config.TELEGRAM_STYLE}

ЗАПИТ КОРИСТУВАЧА:
{user_query}

ВІДПОВІДЬ АКТОРА (Gemini):
{actor_response}

ТВІЙ КРИТИЧНИЙ ВИСНОВОК:"""

            response = await asyncio.to_thread(
                ds_client.chat.completions.create,
                model="deepseek-chat",
                messages=[{"role": "user", "content": synergy_prompt}],
                temperature=0.3
            )
            
            critic_output = response.choices[0].message.content
            
            if "✅ VALIDATED" in critic_output or "VALIDATED" in critic_output:
                # Clean up the label from response if it leaked
                clean_resp = critic_output.replace("✅ VALIDATED", "").replace("VALIDATED", "").strip()
                if not clean_resp: # If it was just the label
                    return actor_response, "♊"
                return clean_resp, "♊+🐋"
            
        except Exception as e:
            logger.warning(f"⚠️ Critic failed: {e}")
            return actor_response, "♊⚠️"

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

        instruction_parts.append("\n### ТВОЇ ОСНОВНІ ІНСТРУКЦІЇ:")
        instruction_parts.append(config.SYSTEM_PROMPT)
        instruction_parts.append("\n" + config.TELEGRAM_STYLE)
        
        return "\n".join(instruction_parts)
