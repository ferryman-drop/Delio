"""
Інтеграційні тести з реальними API ключами для staging
"""
import asyncio
import os
import pytest
import json
from openai import OpenAI
from google import genai
import redis


# Тести для DeepSeek API
def test_deepseek_api():
    """Тест DeepSeek API з реальним ключем"""
    deepseek_key = os.getenv("DEEPSEEK_KEY")
    if not deepseek_key:
        pytest.skip("DEEPSEEK_KEY не встановлено")
    
    client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Say 'OK' only"}],
            max_tokens=10
        )
        assert response.choices[0].message.content
        print(f"✓ DeepSeek API: {response.choices[0].message.content}")
    except Exception as e:
        pytest.fail(f"DeepSeek API failed: {e}")


# Тести для Gemini API
def test_gemini_api():
    """Тест Gemini API з реальним ключем"""
    gemini_key = os.getenv("GEMINI_KEY")
    if not gemini_key:
        pytest.skip("GEMINI_KEY не встановлено")
    
    try:
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Say 'OK' only"
        )
        assert response.text
        print(f"✓ Gemini API: {response.text}")
    except Exception as e:
        # Якщо квота або ліміти — пропускаємо тест (перевірка тексту помилки першочергова)
        if 'RESOURCE_EXHAUSTED' in str(e) or 'quota' in str(e).lower() or '429' in str(e):
            pytest.skip(f"Gemini quota/limit error: {e}")

        # Додаткова перевірка за типом помилки
        try:
            from google.genai import errors as gen_errors
            if isinstance(e, gen_errors.ClientError) and getattr(e, 'status_code', None) == 429:
                pytest.skip(f"Gemini quota exceeded: {e}")
        except Exception:
            pass

        pytest.fail(f"Gemini API failed: {e}")


# Тести для Redis
def test_redis_connection():
    """Тест підключення до Redis"""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    
    try:
        r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True, db=0)
        r.ping()
        print("✓ Redis connection: OK")
    except Exception as e:
        pytest.fail(f"Redis connection failed: {e}")


def test_redis_cache_operations():
    """Тест операцій кеша в Redis"""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    
    try:
        r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True, db=0)
        r.ping()
        
        # Тест set/get
        test_data = {"test": "data", "user_id": 123}
        r.setex("test_key", 3600, json.dumps(test_data))
        
        cached = r.get("test_key")
        assert cached is not None
        assert json.loads(cached) == test_data
        
        # Cleanup
        r.delete("test_key")
        print("✓ Redis cache operations: OK")
    except Exception as e:
        pytest.fail(f"Redis cache operations failed: {e}")


# Тести для комбінації API + кеш
def test_api_with_cache_flow():
    """Інтеграційний тест: API запит + кеш"""
    deepseek_key = os.getenv("DEEPSEEK_KEY")
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    
    if not deepseek_key:
        pytest.skip("DEEPSEEK_KEY не встановлено")
    
    try:
        # Підключення до Redis
        r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True, db=0)
        r.ping()
        
        # DeepSeek запит
        client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Test integration"}],
            max_tokens=20
        )
        
        result = response.choices[0].message.content
        
        # Кеш результату
        cache_key = "integration:test:1"
        r.setex(cache_key, 3600, json.dumps({"response": result}))
        
        # Читання з кеша
        cached_result = r.get(cache_key)
        assert cached_result is not None
        assert json.loads(cached_result)["response"] == result
        
        # Cleanup
        r.delete(cache_key)
        print(f"✓ API + Cache integration: OK")
    except Exception as e:
        pytest.fail(f"API + Cache integration failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
