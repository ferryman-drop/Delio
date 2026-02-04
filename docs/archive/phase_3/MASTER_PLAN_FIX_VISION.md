# 🛠️ ENGINEERING MASTER PLAN: Vision & Stability Fix

## 🎯 Objective
Fix the failure where Vision responses are blocked by (1) Telegram process conflicts and (2) DeepSeek Critic rejection.

## 📋 Execution Steps

### Step 1: Process Cleanup (Rule: ONE Bot)
The system is currently running multiple instances, causing `TelegramConflictError`.
- **Command**:
  ```bash
  sudo systemctl stop lifebot
  pkill -f "python3 main.py"
  pkill -f "python main.py"
  # Verification
  ps aux | grep python
  ```

### Step 2: Critic Logic Update (`core/llm_service.py`)
Direct DeepSeek to accept Image Descriptions as valid.
- **Action**: Locate `synergy_prompt` inside `call_critic`.
- **Add**:
  ```text
  4. ВИНЯТОК: Якщо користувач надіслав ЗОБРАЖЕННЯ (Image/Photo), Актор (Gemini) зобов'язаний описати, що він бачить. Це ВАЛІДНА поведінка.
  ```

### Step 3: Handler UX Improvement (`handlers.py`)
- **Action**: Change `await message.answer("👀 Дивлюся...")` to `await message.answer("📸 *Обробляю зображення...*")`.

### Step 4: Restart & Verify
- **Command**:
  ```bash
  nohup python3 main.py > bot.log 2>&1 &
  tail -f bot.log
  ```
- **Test**: Send the "Polopiryna" photo again.

## 🧪 Success Criteria
1.  Logs show **no** `TelegramConflictError`.
2.  Bot replies with "Обробляю зображення...".
3.  Bot sends a description of the medicine.
4.  Logs show Critic validation passed (or bypassed).
