## ✅ Статус Реалізації (Implementation Status) - Виконано ✅
1. **Vision (👁️)**:
   - `handlers.py`: Реалізовано `handle_photo`, який завантажує зображення та передає шлях через FSM Metadata.
   - `core/llm_service.py`: Оновлено `call_actor` для підтримки `image_path` через Google GenAI SDK.
   - `states/plan.py`: Передача `image_path` з метаданих у `call_actor`.
2. **Voice (🎙️)**:
   - Встановлено бібліотеку `edge-tts`.
   - `core/tts_service.py`: Створено сервіс генерації мови (OstapNeural).
   - `scheduler.py`: Оновлено `send_morning_briefing` — якщо текст > 250 символів, генерується та надсилається голосове повідомлення.
3. **Backup (💾)**:
   - `scripts/freeze_kernel.py`: Створено скрипт бекапу.
   - Успішно створено архів `delio_kernel_2.5.0-Phase3_*.zip`.

### Змінені/Створені файли:
- `handlers.py`
- `core/llm_service.py`
- `core/fsm.py` (Metadata pass-through)
- `core/tts_service.py` (New)
- `scheduler.py`
- `scripts/freeze_kernel.py` (New)


## 🧱 Work Zone

### 1. Task 007: Vision (👁️)
- **File**: `handlers.py`
    - Update Message Handler to accept `F.photo`.
    - Download photo to `/tmp/vision_buffer/`.
- **File**: `core/llm_service.py`
    - Update `call_actor` to accept `image_path`.
    - Use `genai.upload_file` + prompt injection.
- **Rules**:
    - Only process photos if User Trust Level >= 1 (prevent spam).
    - Auto-cleanup `/tmp` after processing.

### 2. Task 008: Voice (🎙️)
- **File**: `core/tts_service.py` (CREATE)
    - Wrapper for `edge_tts`.
    - Function: `generate_speech(text: str, voice="uk-UA-OstapNeural") -> path`.
- **File**: `scheduler.py`
    - Update `send_morning_briefing`: Generate Audio -> Send Voice Message.
- **Constraint**: Text messages > 250 chars in Morning Briefing should be converted to audio.

### 3. Kernel Backup (💾)
- **File**: `scripts/freeze_kernel.py` (CREATE)
    - **Logic**:
        - Walk through `/core`, `/states`, `/tools`.
        - Ignore `__pycache__`, `.git`, `data/*.db` (EXCEPT schemas).
        - Zip into `backups/delio_kernel_v2.5.zip`.
    - **Manifest**: Create `KERNEL_MANIFEST.json` inside zip with version info.

## 📜 Coder Instruction
1.  **Vision First**: Verify you can send a cat photo and Gemini says "It's a cat".
2.  **Voice Second**: Verify `Morning Briefing` comes as a vocal message.
3.  **Backup Last**: Run the script and verify the ZIP size is small (< 2MB) and contains NO user data.

## ⚠️ Safety
- **Vision**: Do not log image binaries to `bot.log`. Log only file paths.
- **Voice**: Ensure `edge-tts` is installed (`pip install edge-tts`).
