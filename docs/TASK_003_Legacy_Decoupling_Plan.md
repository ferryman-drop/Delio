# TASK-003: Decouple Legacy LLM Dependencies (Implementation Plan)

## 🚨 Проблема
Файл `states/plan.py` прямо імпортує `old_core`. Це створює "спагеті-код", де нова архітектура залежить від старої. Це унеможливлює ізольоване тестування FSM і ускладнює майбутню заміну LLM-провайдерів.

## 🛠️ Запропоновані Зміни

### 1. [CREATE] `tools/llm_service.py`
Створити новий адаптер, який інкапсулює роботу з LLM. На першому етапі він може викликати `old_core` всередині, але інтерфейс має бути чистим.

```python
import logging
from typing import Tuple, Optional
import config
# Temporary import until full migration
import old_core as legacy_core 

logger = logging.getLogger("Delio.LLMService")

async def call_actor(
    user_id: int,
    text: str,
    system_instruction: str,
    preferred_model: str = "gemini"
) -> Tuple[str, str]:
    """
    Викликає Actor модель (Gemini/DeepSeek).
    Returns: (response_text, model_label)
    """
    try:
        # Wrapping legacy call
        resp_text, model_used = await legacy_core.call_llm_agentic(
            user_id=user_id,
            text=text,
            system_prompt=system_instruction,
            preferred=preferred_model
        )
        return resp_text, model_used
    except Exception as e:
        logger.error(f"LLM Actor failed: {e}")
        raise

async def call_critic(
    user_query: str,
    actor_response: str,
    instruction: str
) -> Tuple[str, str]:
    """
    Викликає Critic модель (DeepSeek) для валідації.
    """
    # ... (перенести логіку _run_critic з plan.py сюди) ...
    # Див. існуючий код в states/plan.py _run_critic
```

### 2. [MODIFY] `states/plan.py`
Видалити залежність від `old_core` і використовувати `tools.llm_service`.

```python
# REMOVE: import old_core as legacy_core
# ADD:
from tools import llm_service

class PlanState(BaseState):
    async def execute(self, context: ExecutionContext) -> State:
        # ...
        
        # ACTOR PHASE
        # OLD: await legacy_core.call_llm_agentic(...)
        # NEW:
        resp_text, model_used = await llm_service.call_actor(
            user_id=context.user_id,
            text=context.raw_input,
            system_instruction=system_instruction,
            preferred_model=preferred
        )
        
        # CRITIC PHASE
        if config.ENABLE_SYNERGY and "Error" not in model_used:
            # OLD: self._run_critic(...)
            # NEW:
            validated_resp, synergy_label = await llm_service.call_critic(
                user_query=context.raw_input,
                actor_response=resp_text,
                instruction=system_instruction
            )
            # ...
```

### 3. [CLEANUP] `states/plan.py`
Видалити метод `_run_critic` з класу `PlanState`, оскільки він переїхав у `llm_service`.

## 🧪 Verification Plan

### Manual Verification
1. Запустити бота.
2. Надіслати повідомлення.
3. Перевірити логи: має бути успішний виклик через `Delio.LLMService`.
4. Перевірити команду `/agent` (або `/logic`): метадані про модель (іконки ♊/🐋) мають зберегтися.

## ✅ Acceptance Criteria
- [ ] У `states/plan.py` немає імпорту `old_core` або `openai`.
- [ ] `PlanState` делегує всі LLM запити у `llm_service`.
- [ ] Логіка Actor-Critic працює ідентично (синергія зберігається).
