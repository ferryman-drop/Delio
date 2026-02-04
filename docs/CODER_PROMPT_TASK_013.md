# 🛠️ ENGINEERING GUIDE: TASK-013 (Resonance UX & Silhouette UI)

## 🎯 Objective
Transform the interaction from "Static Report" to "Dynamic Voice".
1.  **Silhouette UI**: Replace technical footers with a single "Signature Emoji".
2.  **Fragmentation**: Break responses into "Thoughts" delivered with human-like delays.

## 🧱 Work Zones

### 1. The Silhouette Signature & Technical Silence
- **Action**: REMOVE all `_text_` based model labels and technical blocks.
- **Rule (STRICT)**: Never show "Критичний висновок" or "Critical Conclusion" to the user. This text must be stripped if it leaks from the Critic.
- **Signature Emoji**: Append exactly ONE emoji to the end of the final message.
  - Gemini -> **☂️**
  - Claude -> **🧠**
  - DeepSeek -> **🐋**
  - Error/Timeout -> **⚠️** / **⌛**

### 2. Audio Insight Threshold
- **Goal**: Don't show the "Facts/Questions/Theses" block for short messages.
- **Rule**: 
  - If audio duration < 30 seconds: Send ONLY the response.
  - If audio duration >= 30 seconds: Show the structured "📝 *Розпізнано та очищено:*" block.

### 3. Tone & Improvisation (Anti-Sappy Protocol)
- **Constraint**: Stop using generic phrases like "Що далі?" or "Я готовий допомогти".
- **Instruction**: Delio should assume leadership. Instead of asking, he should suggest or state.
- **Fragmentation**: 
  - First message: Direct answer/info.
  - Second message (3s delay): Improvisation/Refinement.
  - Signature emoji goes on the last message.

### 4. Content Formatting (The Telegram Rule)
- **Action**: Enforce single-asterisk bolding in `config.py` and state prompts.
- **Rule**: ONLY use a single asterisk for bold text (`*текст*`). NEVER use double asterisks (`**текст**`).
- **Logic**: This must be reinforced in the Critic/Judge instructions to ensure they correct any double-asterisk leaks from the Actor.

### 5. Intuitive Mentor Prompting
- **Action**: Update `SYSTEM_PROMPT` in `config.py`.
- **Guideline**: "Do not ask for permission. Make an executive decision based on data, then inform the user."
- **Example**:
  - *Old*: "Do you want to check your tasks?"
  - *New*: "I checked your tasks. You have 3 deadlines. Let's tackle the hardest one first."

### 4. Vision Improvisation (`states/plan.py`)
- **Action**: In `_build_system_instruction` for Vision:
  - Instruct Actor to format output as:
    `[Visual Description]`
    `\n\n`
    `[Philosophical Connection/Improv]`
    `\n\n`
    `[Call to Action]`
- This structure ensures the Fragmentation logic (Zone 2) picks it up automatically.

## 🧪 Verification
1.  **Image Test**: Upload "Bojack".
    - expect: Msg 1 (Description) -> Wait 3s -> Msg 2 (Philosophy) -> Wait 2s -> Msg 3 (Action ☂️).
2.  **UI Check**: Ensure NO text like `(Timeout)` or `Model: Gemini` remains.
