import os
import yaml
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Load Config YAML
yaml_config = {}
try:
    with open('config.yaml', 'r', encoding='utf-8') as f:
        yaml_config = yaml.safe_load(f)
except Exception as e:
    print(f"⚠️ config.yaml missing: {e}")

# --- CONSTANTS ---
TG_TOKEN = os.getenv("TG_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "10"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "30"))
RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", "60"))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_TELEGRAM_ID", "").split(',') if x.strip()]
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# --- MODEL CONFIGURATION (Google GenAI SDK) ---
GEMINI_API_VERSION = "v1alpha" 
MODEL_FAST = "gemini-2.0-flash-lite"      # Tier 1: Super Cheap/Fast
MODEL_BALANCED = "gemini-2.0-flash"       # Tier 2: The Workhorse
MODEL_SMART = "gemini-2.5-pro"            # Tier 3: Complex Reasoning

# Synergy Mode: Gemini generates → DeepSeek analyzes/improves
ENABLE_SYNERGY = os.getenv("ENABLE_SYNERGY", "true").lower() == "true"

# Prompt
SYSTEM_PROMPT = yaml_config.get('context', {}).get('system_prompt', """Ти — Delio AI Assistant (v2.1).
Твоя мета: Максимізувати ефективність та особистий розвиток користувача.
Ти працюєш в 'Синергії': Gemini 2.0 (Швидкість/Креатив) + DeepSeek V3 (Логіка/Код).

[MODES]:
1. ⚡ FAST (Flash Lite): Для простих питань.
2. 🧠 BALANCED (Flash 2.0): Для більшості завдань.
3. 🎓 SMART (Pro 2.5): Для складного аналізу та планування.""")

# Default Aliases
GEMINI_DEFAULT_MODEL = MODEL_BALANCED
DEFAULT_ALIASES = {
    'gemini': GEMINI_DEFAULT_MODEL,
    'g': GEMINI_DEFAULT_MODEL,
    'deepseek': 'deepseek-chat',
    'ds': 'deepseek-chat',
    'local': 'llama3.2:1b',
}
# Merge with YAML
if yaml_config.get('models', {}).get('aliases'):
    DEFAULT_ALIASES.update(yaml_config['models']['aliases'])

# --- LOGGING SETUP ---
def setup_logging():
    logger = logging.getLogger("Delio")
    
    # Only configure if not already configured
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger (fixes duplication)
    logger.propagate = False
    
    # Note: We do NOT add FileHandler because systemd redirects stdout/stderr to bot.log
    # Adding it here would cause duplicate entries (one from app, one from systemd).
    
    return logger

logger = setup_logging()
