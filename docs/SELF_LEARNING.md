# 🤖 SELF-LEARNING СИСТЕМА - ДОКУМЕНТАЦІЯ

## Загальний Огляд

Бот тепер має **систему само-удосконалення** за допомогою 2 AI моделей:
- **Model 1 (Responder):** DeepSeek V3 / Gemini - генерує відповіді
- **Model 2 (Evaluator):** Друга модель - оцінює якість відповідей

---

## 🏗️ АРХІТЕКТУРА SELF-LEARNING

```
┌──────────────────────────────────────────────────────────────┐
│                     User Query                               │
└──────────────────────┬───────────────────────────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │   MODEL 1: RESPONDER         │
        │   ├─ DeepSeek V3            │
        │   └─ або Gemini 1.5 Flash   │
        │   → Генерує відповідь        │
        └──────────────┬──────────────┘
                       │
           ┌───────────▼────────────┐
           │  Відправка користувачу │
           └───────────┬────────────┘
                       │
        ┌──────────────▼──────────────┐
        │   MODEL 2: EVALUATOR         │
        │   (Друга модель)             │
        │   → Оцінює якість (0-10)     │
        │   → Генерує feedback         │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │   SELF-LEARNING DATABASE     │
        │   ├─ response_evaluations    │
        │   ├─ scores & feedback       │
        │   └─ patterns for learning   │
        └──────────────────────────────┘
```

---

## 📊 ТАБЛИЦЯ response_evaluations

Зберігає всі оцінки якості:

```sql
CREATE TABLE response_evaluations (
    id INTEGER PRIMARY KEY,
    message_id INTEGER,              -- Посилання на повідомлення
    user_id INTEGER,                 -- Користувач
    response_quality_score INTEGER,  -- Оцінка (0-10)
    evaluator_model TEXT,            -- Яка модель оцінювала
    evaluation_feedback TEXT,        -- Коментар от evaluator
    user_rating INTEGER,             -- Рейтинг користувача (якщо є)
    timestamp DATETIME               -- Коли оцінено
);
```

---

## 🔍 КРИТЕРІЇ ОЦІНКИ ЯКОСТІ

Evaluator аналізує кожну відповідь за:

1. **Clarity (0-10)** - Ясність
   - Чи зрозуміла відповідь?
   - Чи немає двозначності?

2. **Relevance (0-10)** - Релевантність
   - Чи відповідає на питання?
   - Чи не відхідить від теми?

3. **Actionability (0-10)** - Практичність
   - Чи можна відразу діяти?
   - Чи є конкретні кроки?

4. **Tone Match (0-10)** - Відповідність тону
   - Чи відповідає тону ментора-стратега?
   - Чи структурована як Інсайт→Фреймворк→Дії?

**Overall Score** = середня з 4 критеріїв

---

## 💾 ЗБЕРІГАННЯ ДАНИХ

Кожна відповідь тепер зберігає:

```python
# messages table
{
    user_query: "Як почати стартап?",
    bot_response: "[структурована відповідь]",
    model: "DeepSeek V3"
}

# response_evaluations table
{
    clarity_score: 9,
    relevance_score: 8,
    actionability_score: 9,
    tone_match_score: 8,
    overall_score: 8.5,
    feedback: "Хороша структура, але можна більше конкретики"
}
```

---

## 🚀 АКТИВАЦІЯ SELF-LEARNING

### Вмикається автоматично:

1. **Під час запуску бота:**
   ```bash
   python main.py
   # або
   docker-compose up -d
   ```

2. **На кожну відповідь:**
   - Evaluator оцінює якість
   - Зберігає результати в DB
   - Не блокує користувача (асинхронно)

3. **У фоні (async):**
   ```python
   # Не зупиняє відправку повідомлення
   # Просто зберігає оцінки для аналізу
   evaluation = await evaluate_response_quality(
       user_query, bot_response, model_used
   )
   save_evaluation_to_db(message_id, user_id, evaluation)
   ```

---

## 📈 ЯК ДАНІ ВИКОРИСТОВУЮТЬСЯ

### Поточна реалізація:

1. **Моніторинг якості:**
   ```bash
   sqlite3 data/chat_history.db
   SELECT COUNT(*), AVG(response_quality_score) 
   FROM response_evaluations;
   ```

2. **Аналіз слабих точок:**
   ```bash
   SELECT * FROM response_evaluations 
   WHERE response_quality_score < 6
   ORDER BY timestamp DESC;
   ```

3. **Трендинг:**
   ```bash
   SELECT DATE(timestamp), AVG(response_quality_score)
   FROM response_evaluations
   GROUP BY DATE(timestamp);
   ```

### Майбутнісне:

- **Автоматична регенерація** низькокачісних відповідей (score < 6)
- **Prompt optimization** на основі high-scoring responses
- **A/B тестування** різних стилів
- **Pattern recognition** успішних відповідей

---

## 🔧 КОНФІГУРАЦІЯ

### Вимкнути self-learning оцінку (якщо потрібно):

Закоментуйте в main.py:

```python
# SELF-LEARNING: Асинхронна оцінка якості у фоні
# try:
#     evaluation = await evaluate_response_quality(...)
#     save_evaluation_to_db(msg_id, user_id, evaluation)
# except Exception as eval_err:
#     logger.debug(f"Self-learning evaluation skipped: {eval_err}")
```

### Налаштувати критерії оцінки:

Відредагуйте prompt у `evaluate_response_quality()`:

```python
eval_prompt = f"""Ти - критичний асистент...
[тут налаштуйте критерії]
"""
```

---

## 📊 МОНІТОРИНГ ЯКОСТІ

### Команда для перегляду статистики:

```bash
cd /root/ai_assistant
sqlite3 data/chat_history.db

# Загальна статистика
SELECT 
    COUNT(*) as total_responses,
    AVG(response_quality_score) as avg_score,
    MIN(response_quality_score) as min_score,
    MAX(response_quality_score) as max_score
FROM response_evaluations;

# Оцінки по моделях
SELECT 
    evaluator_model,
    COUNT(*) as evaluations,
    AVG(response_quality_score) as avg_score
FROM response_evaluations
GROUP BY evaluator_model;

# Низькокачісні відповіді (< 6 балів)
SELECT 
    m.user_name,
    m.message,
    m.response,
    e.response_quality_score,
    e.evaluation_feedback,
    e.timestamp
FROM response_evaluations e
JOIN messages m ON e.message_id = m.id
WHERE e.response_quality_score < 6
ORDER BY e.timestamp DESC;
```

---

## 🎯 НАСТУПНІ КРОКИ

### Phase 1 (current):
✅ Evaluation infrastructure  
✅ Quality scoring  
✅ Data persistence  

### Phase 2 (planned):
- [ ] Auto-regeneration (score < 6)
- [ ] Prompt optimization based on patterns
- [ ] A/B testing framework
- [ ] Analytics dashboard

### Phase 3 (advanced):
- [ ] Semantic search for similar queries
- [ ] Dynamic prompt adjustment
- [ ] User feedback loop (👍/👎)
- [ ] Performance trending

---

## 🛠️ DEBUGGING

### Проглянути логи оцінювання:

```bash
tail -f bot_run.log | grep "Evaluation\|evaluation"
```

### Тестовий запуск evaluation:

```python
import asyncio
from main import evaluate_response_quality

query = "Як побудувати бізнес?"
response = "Перший крок: аналіз ринку..."
model = "DeepSeek V3"

result = asyncio.run(evaluate_response_quality(query, response, model))
print(result)
```

### Переконатися що таблиця створена:

```bash
sqlite3 data/chat_history.db ".schema response_evaluations"
```

---

## 💡 TIPS & TRICKS

1. **Оптимізація:** Self-learning запускається асинхронно, не впливаючи на швидкість відповідей

2. **Точність:** Evaluator використовує низьку температуру (0.3) для консистентних оцінок

3. **Масштабування:** JSON парсинг має fallback для невідформатованих відповідей

4. **Мониторинг:** Регулярно перевіряйте `response_quality_score` в DB

---

## 📞 ІНТЕГРАЦІЯ З CHATGPT

Щоб поділитися з ChatGPT:

```markdown
# PROJECT STATUS + SELF-LEARNING IMPLEMENTATION

[вставити PROJECT_STATUS.md]

## SELF-LEARNING SCHEMA

[вставити цей файл]

## ПОТОЧНА БД СХЕМА

[витяг з sqlite3 data/chat_history.db ".schema"]
```

---

**Version:** 2.2.0 - Self-Learning Phase 1  
**Status:** ✅ Fully Operational  
**Ready for:** Analytics, Optimization, User Feedback Integration
