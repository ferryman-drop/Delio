# 🛠️ ENGINEERING GUIDE: Vision Fix & System Cleanup

## 🎯 Context
The user sent a photo of "Polopiryna MAX". The bot downloaded it and started the FSM, but the user received no analysis back. Logs show `TelegramConflictError`, which is the likely cause of response delivery failure.

## 🧱 Work Zone

### 1. Resolve Conflict (CRITICAL)
- **Identify**: Multiple bot instances are running.
- **Action**:
    - Kill all python processes: `pkill -f python3`.
    - Restart only one instance: `python3 main.py`.
    - Check logs to ensure `Conflict` errors are gone.

### 2. Improve Feedback (`handlers.py`)
- Change the static feedback message from "👀 Дивлюся..." to something more professional.
- Use a dynamic emoji to show progress.
- **Code Change**:
```python
msg = await message.answer("📸 *Обробляю зображення...*")
# ... process ...
# Optional: can edit this msg later if FSM allowed editing, 
# but currently FSM is async. Keep it simple.
```

### 3. Respond State Hardening (`states/respond.py`)
- Add a retry mechanism or a clear fallback message if `send_message` fails.
- Log the EXACT content being sent for easier debugging.

### 4. Logic Verification (`states/plan.py`)
- Ensure that if an image is present, Gemini is instructed to prioritize its analysis.
- Verify `context.response` is actually populated by `Actor`.

## 📜 Coder Prompt Rules
- **Rule 1**: Silence the `Conflict` error first. Without it, we can't trust the network.
- **Rule 2**: Log the Gemini raw output to `bot.log` temporarily to see what it said about Polopiryna.

## 🧪 Verification
- Send the same photo again.
- **Expected**: "Обробляю..." follows immediately by a detailed description of the medicine.
