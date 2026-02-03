import logging
import uuid
import sqlite3
from datetime import datetime
import config

logger = logging.getLogger(__name__)

# Cost per 1k tokens (Approx)
COSTS = {
    "gemini-1.5-flash-latest": {"in": 0.000075, "out": 0.0003},
    "gemini-1.5-pro": {"in": 0.00125, "out": 0.005},
    "deepseek-chat": {"in": 0.00014, "out": 0.00028}, # Approx V3
    "llama3.2:1b": {"in": 0, "out": 0}
}
DEFAULT_COST = {"in": 0.0001, "out": 0.0002}

def estimate_tokens(text: str) -> int:
    return len(text) // 4

def calculate_cost(model_name: str, input_tok: int, output_tok: int) -> float:
    # Normalize name
    key = "gemini-1.5-flash-latest"
    if "pro" in model_name.lower(): key = "gemini-1.5-pro"
    elif "deepseek" in model_name.lower(): key = "deepseek-chat"
    elif "llama" in model_name.lower(): key = "llama3.2:1b"
    
    rates = COSTS.get(key, DEFAULT_COST)
    cost = (input_tok / 1000 * rates["in"]) + (output_tok / 1000 * rates["out"])
    return round(cost, 6)

def log_routing_event(user_id, life_level, complexity, model, in_txt, out_txt):
    try:
        in_tok = estimate_tokens(in_txt)
        out_tok = estimate_tokens(out_txt)
        cost = calculate_cost(model, in_tok, out_tok)
        
        # We need DB access. Quick connect.
        import memory_manager
        conn = memory_manager.MemoryController().get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO routing_events (id, user_id, timestamp, life_level, complexity, model_selected, input_tokens, output_tokens, cost_est, auditor_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            user_id,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            life_level,
            complexity,
            model,
            in_tok,
            out_tok,
            cost,
            None # Score added later by Learner or Auditor update
        ))
        conn.commit()
        conn.close()
        
        return cost
    except Exception as e:
        logger.error(f"Telemetry Error: {e}")
        return 0.0
