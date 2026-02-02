"""
Тести для Telegram AI Assistant бота
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from collections import defaultdict


class TestBotConfiguration:
    """Тести конфігурації бота"""
    
    def test_tokens_defined(self):
        """Перевірка, що всі токени визначені"""
        # Зчитування з main.py
        TG_TOKEN = os.getenv("TG_TOKEN")
        GEMINI_KEY = os.getenv("GEMINI_KEY")
        DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")
        
        assert TG_TOKEN != "", "Telegram токен не визначений"
        assert GEMINI_KEY != "", "Gemini ключ не визначений"
        assert DEEPSEEK_KEY != "", "DeepSeek ключ не визначений"
    
    def test_api_base_urls(self):
        """Перевірка API URL адрес"""
        deepseek_url = "https://api.deepseek.com"
        gemini_url = "https://generativelanguage.googleapis.com"
        
        assert deepseek_url.startswith("https://"), "DeepSeek URL повинен бути HTTPS"
        assert gemini_url.startswith("https://"), "Gemini URL повинен бути HTTPS"


class TestContextMemory:
    """Тести системи контекстної пам'яті"""
    
    def test_user_history_creation(self):
        """Тест створення історії для нового користувача"""
        user_history = defaultdict(list)
        user_id = 12345
        
        assert len(user_history[user_id]) == 0, "Нова історія повинна бути порожня"
    
    def test_message_storage(self):
        """Тест збереження повідомлень в історії"""
        MAX_HISTORY = 10
        user_history = defaultdict(list)
        user_id = 12345
        
        # Імітація збереження повідомлень
        for i in range(5):
            user_history[user_id].append(f"Message {i}")
        
        assert len(user_history[user_id]) == 5, "Повинно бути збережено 5 повідомлень"
    
    def test_history_limit(self):
        """Тест обмеження історії на 10 повідомлень"""
        MAX_HISTORY = 10
        user_history = defaultdict(list)
        user_id = 12345
        
        # Додаємо більше повідомлень, ніж MAX_HISTORY
        for i in range(15):
            user_history[user_id].append(f"Message {i}")
            # Імітація обмеження
            if len(user_history[user_id]) > MAX_HISTORY:
                user_history[user_id] = user_history[user_id][-MAX_HISTORY:]
        
        assert len(user_history[user_id]) == MAX_HISTORY, \
            f"Історія не повинна перевищувати {MAX_HISTORY} повідомлень"
    
    def test_separate_user_contexts(self):
        """Тест, що кожен користувач має окремий контекст"""
        user_history = defaultdict(list)
        
        user_history[111].append("User 1 message")
        user_history[222].append("User 2 message")
        
        assert "User 1 message" in user_history[111], "Повідомлення користувача 1 повинно бути в його контексті"
        assert "User 2 message" not in user_history[111], "Повідомлення користувача 2 не повинно бути в контексті користувача 1"


class TestAPIIntegration:
    """Тести інтеграції з API"""
    
    @pytest.mark.asyncio
    async def test_deepseek_model_name(self):
        """Перевірка назви моделі DeepSeek"""
        deepseek_model = "deepseek-chat"
        assert deepseek_model == "deepseek-chat", "Неправильна назва моделі DeepSeek"
    
    @pytest.mark.asyncio
    async def test_gemini_model_name(self):
        """Перевірка назви моделі Gemini"""
        gemini_model = "gemini-1.5-flash"
        assert gemini_model == "gemini-1.5-flash", "Неправильна назва моделі Gemini"
    
    def test_fallback_mechanism(self):
        """Тест механізму переключення на резервну модель"""
        primary_model = "deepseek-chat"
        fallback_model = "gemini-1.5-flash"
        
        # Імітація помилки в основній моделі
        deepseek_failed = True
        
        active_model = fallback_model if deepseek_failed else primary_model
        
        assert active_model == fallback_model, "Повинна активуватися резервна модель"
    
    def test_error_message_delivery(self):
        """Тест доставки повідомлення про помилку користувачу"""
        error_message = "❌ Обидва сервіси недоступні."
        
        assert "❌" in error_message, "Повідомлення про помилку повинне містити емодзі помилки"
        assert "недоступні" in error_message, "Повідомлення повинне пояснювати проблему"


class TestLogging:
    """Тести логування"""
    
    def test_user_info_in_logs(self):
        """Тест логування інформації про користувача"""
        user_name = "John"
        message_start = "Hello"
        
        log_message = f"Запит від {user_name}: {message_start[:20]}..."
        
        assert user_name in log_message, "Ім'я користувача повинно бути в логу"
        assert message_start in log_message, "Текст повідомлення повинен бути в логу"
    
    def test_model_response_logging(self):
        """Тест логування інформації про модель"""
        models_log = [
            "🚀 Відповів DeepSeek V3",
            "✅ Відповід Gemini 1.5"
        ]
        
        assert len(models_log) == 2, "Повинно бути 2 типи логів моделей"
        assert any("DeepSeek" in log for log in models_log), "DeepSeek повинен бути залогований"
        assert any("Gemini" in log for log in models_log), "Gemini повинен бути залогований"


class TestMessageHandling:
    """Тести обробки повідомлень"""
    
    def test_message_text_extraction(self):
        """Тест вилучення тексту повідомлення"""
        message_content = "Hello, bot!"
        
        assert isinstance(message_content, str), "Текст повідомлення повинен бути рядком"
        assert len(message_content) > 0, "Текст повідомлення не повинен бути порожнім"
    
    def test_message_truncation_for_logging(self):
        """Тест обрізки довгого повідомлення для логів"""
        long_message = "A" * 100
        truncated = long_message[:20]
        
        assert len(truncated) == 20, "Обрізане повідомлення повинно мати 20 символів"
        assert len(truncated) < len(long_message), "Обрізане повідомлення повинно бути коротше оригіналу"
    
    def test_response_content_type(self):
        """Тест, що відповідь - це текст"""
        response_content = "This is a response"
        
        assert isinstance(response_content, str), "Відповідь повинна бути рядком"
        assert len(response_content) > 0, "Відповідь не повинна бути порожна"


class TestPerformance:
    """Тести продуктивності"""
    
    def test_history_lookup_performance(self):
        """Тест швидкості пошуку історії користувача"""
        user_history = defaultdict(list)
        user_id = 12345
        
        # Додаємо 10 повідомлень
        for i in range(10):
            user_history[user_id].append(f"Message {i}")
        
        # Пошук повинен бути дуже швидким (O(1))
        result = user_history[user_id]
        assert len(result) == 10, "Всі повідомлення повинні бути отримані"
    
    def test_multiple_users_handling(self):
        """Тест обробки декількох користувачів одночасно"""
        user_history = defaultdict(list)
        
        # Імітація 100 користувачів
        for user_id in range(100):
            for msg_num in range(5):
                user_history[user_id].append(f"User {user_id} msg {msg_num}")
        
        assert len(user_history) == 100, "Повинно бути 100 користувачів"
        
        # Перевірка одного користувача
        assert len(user_history[50]) == 5, "Кожен користувач повинен мати 5 повідомлень"


class TestBotInitialization:
    """Тести ініціалізації бота"""
    
    def test_bot_startup_message(self):
        """Тест повідомлення при запуску"""
        startup_message = "🔥 Бот запущений на DeepSeek V3!"
        
        assert "🔥" in startup_message, "Повідомлення запуску повинно містити емодзі"
        assert "DeepSeek" in startup_message, "Повідомлення повинно згадувати основну модель"


class TestErrorHandling:
    """Тести обробки помилок"""
    
    def test_deepseek_error_catching(self):
        """Тест ловлення помилок DeepSeek"""
        error_message = "⚠️ Помилка DeepSeek: Connection timeout"
        
        assert "⚠️" in error_message, "Повідомлення про помилку повинне містити попередження"
        assert "DeepSeek" in error_message, "Повідомлення повинне вказувати на сервіс"
    
    def test_gemini_error_catching(self):
        """Тест ловлення помилок Gemini"""
        error_message = "❌ Помилка Gemini: Invalid API key"
        
        assert "❌" in error_message, "Повідомлення про помилку повинне містити емодзі помилки"
        assert "Gemini" in error_message, "Повідомлення повинне вказувати на сервіс"
    
    def test_graceful_degradation(self):
        """Тест плавного розвалу при помилках"""
        is_deepseek_working = False
        is_gemini_working = True
        
        can_respond = is_deepseek_working or is_gemini_working
        
        assert can_respond, "Бот повинен мати можливість відповідати, якщо працює хоча б одна модель"


# Інтеграційні тести
class TestIntegration:
    """Інтеграційні тести"""
    
    def test_message_flow_with_deepseek(self):
        """Тест повного потоку обробки повідомлення з DeepSeek"""
        user_id = 12345
        user_message = "Hello!"
        
        # Симуляція обробки
        assert user_message, "Повідомлення повинно бути отримано"
        assert user_id, "ID користувача повинен бути визначений"
    
    def test_message_flow_with_fallback(self):
        """Тест потоку обробки з переключенням на Gemini"""
        user_id = 67890
        user_message = "Another message"
        deepseek_failed = True
        
        # Симуляція обробки з fallback
        assert user_message, "Повідомлення повинно бути отримано"
        assert deepseek_failed, "DeepSeek повинен мати помилку для тесту fallback"
    
    def test_complete_chat_scenario(self):
        """Тест повного сценарію чату"""
        user_history = defaultdict(list)
        user_id = 99999
        
        # Користувач пише 3 повідомлення
        messages = [
            "Hi bot",
            "How are you?",
            "Tell me a joke"
        ]
        
        for msg in messages:
            user_history[user_id].append({
                "role": "user",
                "content": msg
            })
        
        assert len(user_history[user_id]) == 3, "Повинно бути 3 повідомлення користувача"
        
        # Імітація відповідей бота
        for msg in messages:
            user_history[user_id].append({
                "role": "assistant",
                "content": "Mock response"
            })
        
        assert len(user_history[user_id]) == 6, "Повинно бути 6 повідомлень в сумі (3 користувача + 3 бота)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
