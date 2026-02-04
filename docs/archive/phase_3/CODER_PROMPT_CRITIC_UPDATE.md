# 🛠️ ENGINEERING GUIDE: Relaxing Critic for Vision

## 🎯 Context
The Vision module works (Gemini sees the image), but the Critic (DeepSeek) rejects the response as "Out of Context" or "Off-Topic" because it adheres strictly to the "Life Coach" persona. We need to teach the Critic that **describing an uploaded image** is a valid action.

## 🧱 Work Zone
- **File**: `core/llm_service.py`
- **Function**: `call_critic`

## 📜 Coder Prompt Rules

### 1. Update `synergy_prompt`
Add a specific exception rule for Image/Multimedia handling.

**Current:**
```text
3. Звертай увагу на точність фактів та відповідність Life Level користувача.
```

**New:**
```text
3. Звертай увагу на точність фактів та відповідність Life Level користувача.
4. ВИНЯТОК: Якщо користувач надіслав ЗОБРАЖЕННЯ (Image/Photo), Актор (Gemini) зобов'язаний описати, що він бачить. Це ВАЛІДНА поведінка. Не блокуй опис фотографій як "порушення контексту".
```

### 2. Verification
- Verify that the Critic no longer replies with "ВІДХИЛЕНО: Повна невідповідність контексту" when analyzing a photo.

## 🧪 Expected Behavior
- User sends photo -> Bot says "Обробляю..." -> Bot answers: "Це Polopiryna Max, засіб від застуди..." -> Critic adds label "✅ VALIDATED" (hidden) or passes it through.
