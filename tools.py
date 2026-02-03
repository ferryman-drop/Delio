
import logging
from duckduckgo_search import DDGS
from RestrictedPython import compile_restricted, safe_builtins
from RestrictedPython.Guards import guarded_iter_unpack_sequence, safe_globals
import sys
import asyncio
from contextlib import redirect_stdout, redirect_stderr
from core.state_guard import guard, Action

# Shim for AsyncDDGS if missing in newer versions of duckduckgo_search
try:
    from duckduckgo_search import AsyncDDGS
except ImportError:
    class AsyncDDGS(DDGS):
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        async def text(self, *args, **kwargs):
            return await asyncio.to_thread(super().text, *args, **kwargs)

logger = logging.getLogger(__name__)

async def search_web(query: str, user_id: int, max_results: int = 5) -> str:
    """
    Пошук інформації в інтернеті через DuckDuckGo (Асинхронно).
    
    Args:
        query: Рядок пошукового запиту.
        user_id: ID користувача Telegram.
        max_results: Максимальна кількість результатів (за замовчуванням 5).
    """
    guard.assert_allowed(user_id, Action.NETWORK)
    try:
        logger.info(f"🔍 Searching web for: {query}")
        
        if not query or not query.strip():
            return "❌ Запит не може бути порожнім."
        
        async with AsyncDDGS() as ddgs:
            results = await ddgs.text(query, max_results=max_results)
        
        if not results:
            return f"❌ Нічого не знайдено для '{query}'."
        
        output = f"🔍 Результати пошуку для '{query}':\n\n"
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            snippet = result.get('body', 'No description')
            url = result.get('href', '')
            output += f"{i}. **{title}**\n{snippet}\n🔗 {url}\n\n"
        
        return output.strip()
    except Exception as e:
        logger.error(f"❌ Search error: {e}")
        return f"❌ Помилка пошуку: {str(e)}"

async def execute_python(code: str, user_id: int, timeout: int = 15) -> str:
    """
    Виконання коду на Python в ізольованому середовищі (Асинхронно).
    
    Args:
        code: Повний код на Python для виконання.
        user_id: ID користувача Telegram.
        timeout: Час виконання в секундах (за замовчуванням 15).
    """
    guard.assert_allowed(user_id, Action.DOCKER)
    import tempfile
    import os
    
    try:
        logger.info(f"🐍 Executing Python code (Async)")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            process = await asyncio.create_subprocess_exec(
                'python3', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={'PYTHONPATH': ''}
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                output = stdout.decode().strip()
                errors = stderr.decode().strip()
                
                if process.returncode != 0:
                    return f"❌ Помилка виконання:\n{errors}" if errors else f"❌ Код завершився з помилкою (код {process.returncode})"
                
                if errors:
                    return f"⚠️ Попередження:\n{errors}\n\nВивід:\n{output}" if output else f"⚠️ Попередження:\n{errors}"
                
                return f"✅ Результат:\n{output}" if output else "✅ Код виконано успішно (без виводу)"
                
            except asyncio.TimeoutExpired:
                process.kill()
                return f"❌ Час виконання перевищено ({timeout}с)"
                
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    except Exception as e:
        logger.error(f"❌ Execution error: {e}")
        return f"❌ Помилка виконання: {str(e)}"

def switch_model(user_id: int, model_name: str) -> str:
    """
    Змінити поточну модель користувача (gemini, deepseek або auto).
    Використовуйте цей інструмент, якщо користувач явно просить змінити модель.
    
    Args:
        user_id: ID користувача Telegram (має бути цілим числом).
        model_name: Назва моделі ('gemini', 'deepseek' або 'auto').
    """
    import prefs
    try:
        model_name = model_name.lower().strip()
        target = "" if model_name == "auto" else model_name
        prefs.set_user_pref(int(user_id), target)
        return f"✅ Модель успішно змінено на {model_name}. Наступні відповіді будуть від цієї моделі."
    except Exception as e:
        return f"❌ Помилка при зміні моделі: {str(e)}"

def list_project_dir(user_id: int, path: str = ".") -> str:
    """
    Показати список файлів у проекті (Адмін-інструмент).
    
    Args:
        user_id: ID користувача Telegram.
        path: Відносний шлях до папки (за замовчуванням '.').
    """
    guard.assert_allowed(user_id, Action.FS_READ)
    import roles
    import os
    if not roles.is_admin(int(user_id)):
        return "❌ Доступ заборонено. Цей інструмент лише для адміністраторів."
    
    try:
        items = os.listdir(path)
        return "📁 Вміст папки:\n" + "\n".join([f"- {i}" for i in items])
    except Exception as e:
        return f"❌ Помилка: {str(e)}"

def read_project_file(user_id: int, filepath: str) -> str:
    """
    Прочитати вміст файлу проекту (Адмін-інструмент).
    
    Args:
        user_id: ID користувача Telegram.
        filepath: Шлях до файлу.
    """
    guard.assert_allowed(user_id, Action.FS_READ)
    import roles
    if not roles.is_admin(int(user_id)):
        return "❌ Доступ заборонено. Цей інструмент лише для адміністраторів."
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"📄 Файл: {filepath}\n\n```python\n{content}\n```"
    except Exception as e:
        return f"❌ Помилка читання: {str(e)}"

def edit_project_file(user_id: int, filepath: str, search_text: str, replace_text: str) -> str:
    """
    Редагувати файл проекту (Адмін-інструмент). Пошук і заміна тексту.
    
    Args:
        user_id: ID користувача Telegram.
        filepath: Шлях до файлу.
        search_text: Текст, який треба замінити.
        replace_text: Новий текст.
    """
    guard.assert_allowed(user_id, Action.FS_WRITE)
    import roles
    if not roles.is_admin(int(user_id)):
        return "❌ Доступ заборонено. Цей інструмент лише для адміністраторів."
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if search_text not in content:
            return f"❌ Текст для заміни не знайдено у файлі {filepath}."
            
        new_content = content.replace(search_text, replace_text)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return f"✅ Файл {filepath} успішно оновлено."
    except Exception as e:
        return f"❌ Помилка редагування: {str(e)}"

def run_terminal_command(user_id: int, command: str) -> str:
    """
    Виконати будь-яку команду в терміналі сервера (Адмін-інструмент).
    Може використовуватися для перезапуску бота (systemctl restart ai_assistant) тощо.
    
    Args:
        user_id: ID користувача Telegram.
        command: Команда для виконання.
    """
    guard.assert_allowed(user_id, Action.NETWORK) # Treat terminal as external action
    import roles
    import subprocess
    if not roles.is_admin(int(user_id)):
        return "❌ Доступ заборонено. Цей інструмент лише для адміністраторів."
    
    try:
        logger.info(f"💾 Admin executing terminal command: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        return f"🖥️ Термінал:\n\n```\n{output or '(немає виводу)'}\n```"
    except Exception as e:
        return f"❌ Помилка терміналу: {str(e)}"

def save_user_note(user_id: int, content: str, topic: str = "general") -> str:
    """
    Зберегти важливу інформацію або нотатку про користувача.
    Використовуйте це, коли користувач просить 'запам'ятати' щось важливе.
    
    Args:
        user_id: ID користувача Telegram.
        content: Зміст нотатки.
        topic: Тема нотатки (наприклад, 'особисте', 'робота', 'паролі' - не для секретів!).
    """
    guard.assert_allowed(user_id, Action.MEMORY_WRITE)
    import memory
    import memory_manager
    try:
        # 1. Save to Vector DB (for search)
        vec_success = memory.save_note(int(user_id), content, topic)
        
        # 2. Save to SQLite (for persistence)
        sql_success = memory_manager.global_memory.add_note(int(user_id), content, topic)
        
        if vec_success or sql_success:
            return f"✅ Нотатку збережено: '{content}' (Тема: {topic})"
        else:
            return "❌ Не вдалося зберегти нотатку (DB Error)."
    except Exception as e:
        return f"❌ Помилка: {str(e)}"

def search_user_notes(user_id: int, query: str) -> str:
    """
    Пошук серед збережених нотаток користувача.
    Використовуйте це, щоб згадати факти, які ви просили раніше запам'ятати.
    
    Args:
        user_id: ID користувача Telegram.
        query: Запит для пошуку в нотатках.
    """
    import memory
    try:
        results = memory.search_notes(int(user_id), query)
        if not results:
            return f"❓ Нотаток за запитом '{query}' не знайдено."
        
        output = f"📌 Знайдені нотатки:\n"
        for i, res in enumerate(results, 1):
            output += f"{i}. {res}\n"
        return output.strip()
    except Exception as e:
        return f"❌ Помилка пошуку: {str(e)}"

def log_decision(user_id: int, topic: str, context: str, rationale: str, outcome: str, status: str = 'active', tags: str = "") -> str:
    """
    Зафіксувати стратегічне рішення, прийняте під час розмови.
    Використовуйте це для фіксації важливих планів, поворотів (pivots) або бізнес-рішень.
    
    Args:
        user_id: ID користувача Telegram.
        topic: Короткий заголовок (наприклад, 'Фокус на B2B').
        context: Передумови (чому це зараз актуально).
        rationale: Обґрунтування (чому обрано саме цей шлях).
        outcome: Очікуваний результат (KPI, ROI, мета).
        status: Статус рішення ('active', 'completed', 'failed').
        tags: Теги через кому (наприклад, 'стратегія, b2b, фокус').
    """
    import memory_manager
    try:
        tag_list = [t.strip() for t in tags.split(",")] if tags else []
        success = memory_manager.add_decision(int(user_id), topic, context, rationale, outcome, status, tag_list)
        if success:
            return f"✅ Стратегічне рішення зафіксовано: '{topic}'"
        return "❌ Не вдалося зафіксувати рішення."
    except Exception as e:
        return f"❌ Помилка: {str(e)}"

def log_insight(user_id: int, insight_type: str, description: str, evidence: str, recommendation: str) -> str:
    """
    Зафіксувати важливе спостереження (інсайт) про користувача або проект.
    Використовуйте для виявлення патернів, суперечностей або нових можливостей.
    
    Args:
        user_id: ID користувача Telegram.
        insight_type: Тип ('pattern', 'contradiction', 'opportunity').
        description: Суть інсайту.
        evidence: Докази (на основі чого зроблено висновок).
        recommendation: Рекомендація (що з цим робити).
    """
    import memory_manager
    try:
        success = memory_manager.add_insight(int(user_id), insight_type, description, evidence, recommendation)
        if success:
            return f"💡 Інсайт зафіксовано: {description[:50]}..."
        return "❌ Не вдалося зафіксувати інсайт."
    except Exception as e:
        return f"❌ Помилка: {str(e)}"

def update_user_profile(user_id: int, core_values: str = "", goals: str = "", patterns: str = "") -> str:
    """
    Оновити стратегічний профіль користувача (цінності, цілі, патерни).
    
    Args:
        user_id: ID користувача Telegram.
        core_values: Основні цінності через кому.
        goals: Довгострокові цілі через кому.
        patterns: Патерни мислення через кому.
    """
    import memory_manager
    try:
        val_list = [s.strip() for s in core_values.split(",")] if core_values else None
        goal_list = [s.strip() for s in goals.split(",")] if goals else None
        pat_list = [s.strip() for s in patterns.split(",")] if patterns else None
        
        success = memory_manager.update_profile(int(user_id), val_list, goal_list, pat_list)
        if success:
            return "✅ Профіль успішно оновлено."
        return "❌ Не вдалося оновити профіль."
    except Exception as e:
        return f"❌ Помилка: {str(e)}"

def add_task(user_id: int, title: str, priority: str = 'med', due_date: str = None) -> str:
    """
    Додати нове завдання в список.
    
    Args:
        user_id: ID користувача.
        title: Назва завдання.
        priority: Пріоритет ('high', 'med', 'low').
        due_date: Дата виконання (ISO 8601 string, e.g. '2023-10-31 18:00').
    """
    import task_manager
    try:
        t_id = task_manager.task_system.add_task(int(user_id), title, priority, due_date)
        if t_id: return f"✅ Завдання додано: {title} (ID: {t_id[:5]})"
        return "❌ Помилка додавання завдання."
    except Exception as e:
        return f"❌ Помилка: {e}"

def list_tasks(user_id: int, status: str = 'pending', limit: int = 10) -> str:
    """
    Показати список завдань.
    
    Args:
        user_id: ID користувача.
        status: Фільтр ('pending', 'done', 'all').
        limit: Кількість завдань.
    """
    import task_manager
    try:
        tasks = task_manager.task_system.list_tasks(int(user_id), status, int(limit))
        if not tasks: return "ℹ️ Завдань немає."
        
        output = f"📋 Список завдань ({status}):\n"
        for t in tasks:
             due = f" [Due: {t['due']}]" if t['due'] else ""
             output += f"- [{t['priority'].upper()}] {t['title']} {due} (ID: {t['id'][:5]})\n"
        return output.strip()
    except Exception as e:
        return f"❌ Помилка: {e}"

def complete_task(user_id: int, task_id_or_title: str) -> str:
    """
    Відмітити завдання як виконане.
    
    Args:
        user_id: ID користувача.
        task_id_or_title: ID завдання (перші 5 символів) або частина назви.
    """
    import task_manager
    try:
        title = task_manager.task_system.complete_task(int(user_id), task_id_or_title)
        if title: return f"🎉 Чудова робота! Завдання '{title}' виконано."
        return f"❌ Завдання не знайдено: {task_id_or_title}"
    except Exception as e:
        return f"❌ Помилка: {e}"

def schedule_event(user_id: int, title: str, start_time: str, duration_minutes: int = 60) -> str:
    """
    Запланувати подію (генерує ICS або додає в Google Calendar).
    
    Args:
        user_id: ID користувача.
        title: Назва події.
        start_time: Час початку (ISO string, e.g. '2023-10-31 18:00').
        duration_minutes: Тривалість у хвилинах.
    """
    # This invokes the Hybrid Logic (Google -> ICS)
    import calendar_manager
    try:
        result = calendar_manager.calendar_system.schedule_event(int(user_id), title, start_time, duration_minutes)
        return result
    except Exception as e:
        # If calendar_manager fails to import or other error
        return f"❌ Помилка календаря: {e}"

# Definitions for Gemini Tool Use
TOOLS_LIST = [
    search_web, execute_python, switch_model,
    list_project_dir, read_project_file, edit_project_file, run_terminal_command,
    save_user_note, search_user_notes, 
    log_decision, log_insight, update_user_profile,
    add_task, list_tasks, complete_task, schedule_event
]
