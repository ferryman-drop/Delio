# 🛠️ ENGINEERING GUIDE: TASK-011 (Claude Integration)

## 🎯 Context
We are adding **Claude 3.5 Sonnet** to the AI Assistant's model roster.
Role: **The Judge / Mentor**.
Capabilities: High nuance, excellent code gen, ethical reasoning.

## 🧱 Work Zones

### 1. Dependencies
- **Action**: Install `anthropic` library.
- **Command**: `pip install anthropic` (and update `requirements.txt`).

### 2. `core/llm_service.py`
- **Goal**: Add `call_judge` function.
- **Logic**:
  - Initialize `anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_KEY)`.
  - Model: `claude-3-5-sonnet-20240620`.
  - System Prompt: "You are the Wise Judge. Your goal is to refine the Actor's output and double-check the Critic's feedback."

### 3. `call_critic` Update
- **Goal**: Allow fallback or escalation to Claude.
- **Modification**: If DeepSeek fails (timeout/error) OR if the complexity is "HIGH", we might want to route to Claude instead.
- For now, let's keep it simple: Add `call_judge` as a separate tool, and maybe add a flag to `call_actor` to use Claude directly if `preferred_model='claude'`.

### 4. `config.py`
- Add `ANTHROPIC_KEY`.
- Add `MODEL_JUDGE = "claude-3-5-sonnet-20240620"`.

## 🧪 Verification Plan
1.  **Test Script**: Create `scripts/test_claude.py`.
2.  **Execution**: Run script to verify API connection.
3.  **Output**: Claude should reply with a short poem about "The Triumvirate of AI".

## 📜 Coder Prompt Rules
- **Rule 1**: Use `AsyncAnthropic` client.
- **Rule 2**: Handle `AuthenticationError` gracefully.
