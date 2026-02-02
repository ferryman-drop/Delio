# 🚀 SETUP GUIDE - Коротка інструкція запуску

## 📋 Що в проекті

✅ **Rate limiting** — обмеження запитів (30/60сек)  
✅ **Dockerization** — контейнеризація (Docker + docker-compose)  
✅ **Admin commands** — управління ботом (mute, broadcast, stats)  
✅ **Log rotation** — автоматична ротація логів (5MB, 7 файлів)  
✅ **Redis cache** — кеширування контексту (24h TTL)  
✅ **CI/CD** — GitHub Actions з тестами  
✅ **Integration tests** — тести з реальними API  

---

## 🎯 ШВИДКИЙ СТАРТ (5 хвилин)

### 1. Готуємо файл `.env`
```bash
cp .env.example .env
nano .env
```

**Обов'язково заповніть:**
```
TG_TOKEN=ваш_токен_від_@BotFather
DEEPSEEK_KEY=ваш_ключ_deepseek
GEMINI_KEY=ваш_ключ_gemini
ADMIN_TELEGRAM_ID=ваш_user_id
```

**Опціонально:**
```
REDIS_HOST=localhost
REDIS_PORT=6379
LOG_LEVEL=INFO
MAX_HISTORY=10
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_PERIOD=60
```

---

## 🐳 OPTION A: Docker (рекомендовано)

```bash
# Запуск
docker-compose up -d

# Логи
docker-compose logs -f bot

# Зупинення
docker-compose down
```

**Redis автоматично стартує з botом!**

---

## 🖥️ OPTION B: Локально (development)

### Установка
```bash
# Віртуальне оточення
python3 -m venv venv
source venv/bin/activate

# Залежності
pip install -r requirements.txt

# Redis (окремо, якщо потрібен)
redis-server  # або через Docker: docker run -d -p 6379:6379 redis:7-alpine
```

### Запуск бота
```bash
python main.py
```

### Логи
```bash
tail -f bot.log
```

---

## 🧪 ТЕСТУВАННЯ

### Модульні тести
```bash
pytest test_bot.py -v
```

### Інтеграційні тести (потребує ключів)
```bash
# Экспортуємо ключі
export DEEPSEEK_KEY="..."
export GEMINI_KEY="..."

# Запуск
pytest test_integration.py -v
```

### Перевірка синтаксису
```bash
python -m py_compile main.py test_*.py
```

---

## 🤖 КОМАНДИ БОТА

| Команда | Функція |
|---------|---------|
| `/start` | Старт |
| `/help` | Допомога |
| `/history` | Останні 5 повідомлень |
| `/clear` | Очистити контекст |
| `/stats` | Статистика користувача |
| `/mute @user` | Заблокувати користувача (admin) |
| `/unmute @user` | Розблокувати (admin) |
| `/broadcast текст` | Оповістити всіх (admin) |

---

## 📊 АРХІТЕКТУРА

```
Користувач
    ↓
Bot (aiogram)
    ↓
Rate Limiting ← SQLite (история)
    ↓
DeepSeek API ← Redis Cache (контекст 24h)
    ↓ (fallback)
Gemini API
    ↓
Логування (bot.log, ротація 5MB/7 файлів)
```

---

## 🔍 МОНІТОРИНГ

### Логи
```bash
tail -f bot.log          # Реал-тайм
grep ERROR bot.log       # Помилки
grep "Rate limit" bot.log # Заблокувані
```

### Redis (якщо потрібно)
```bash
redis-cli
> KEYS *
> GET context:USER_ID
```

### SQLite (історія)
```bash
sqlite3 data/chat_history.db
> SELECT * FROM messages LIMIT 10;
> SELECT * FROM users;
```

---

## 🚨 TROUBLESHOOTING

| Проблема | Рішення |
|----------|---------|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| Redis недоступний | Бот буде працювати без кеша (fallback) |
| Логи не пишуться | Перевірьте права на папку, `LOG_LEVEL=DEBUG` |
| Тести падають | Перевірьте `.env`, запустіть `pytest -v` |
| Bot не запускається | Перевірьте `TG_TOKEN`, логи `bot.log` |

---

## 📁 ФАЙЛИ ПРОЕКТУ

```
ai_assistant/
├── main.py                    # Основний код (RotatingFileHandler + Redis)
├── requirements.txt           # Залежності (+ redis)
├── .env.example              # Шаблон конфігу
├── config.yaml               # Основні параметри
├── docker-compose.yml        # Docker Compose (+ Redis сервіс)
├── Dockerfile                # Docker образ
├── logrotate.conf            # Конфіг ротації логів
├── test_bot.py               # Модульні тести (24 тести)
├── test_integration.py       # Інтеграційні тести
├── .github/workflows/ci.yml  # GitHub Actions (автотести)
├── ASSISTANT_ROLE.md         # Персона асистента
├── QUICKSTART.md             # Детальний гайд
└── CHANGES.md                # Журнал змін (версія 2.1.0)
```

---

## ✅ СТАТУС

- ✅ Rate limiting
- ✅ Dockerization  
- ✅ Admin commands + inline buttons
- ✅ Log rotation (RotatingFileHandler)
- ✅ Redis cache (24h TTL, fallback на in-memory)
- ✅ CI/CD (GitHub Actions з Redis сервісом)
- ✅ Integration tests (API + Cache + Redis)
- ✅ Документація

**Всі 24 модульні тести пройдені ✅**

---

## 📞 ВАЖЛИВО

1. **Ключі API**: Отримайте з:
   - Telegram: @BotFather
   - DeepSeek: https://platform.deepseek.com/
   - Gemini: https://aistudio.google.com/app/apikey

2. **Admin ID**: Напишіть боту `/start` і подивіться логи для вашого ID

3. **Redis**: Якщо немає, бот працюватиме без кеша

4. **CI**: Добавьте ключи в GitHub Secrets для автотестів

---

**Версія:** 2.1.0  
**Останнє оновлення:** 31 січня 2026  
**Статус:** Production Ready ✅
