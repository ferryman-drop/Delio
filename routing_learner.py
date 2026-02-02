import json
import logging
import os
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

WEIGHTS_FILE = os.path.join(os.getcwd(), 'data', 'routing_weights.json')
DB_PATH = os.path.join(os.getcwd(), 'data', 'bot_data.db')

DEFAULT_WEIGHTS = {
    # Format: "{LifeLevel}_{Complexity}_{Model}"
    "L1_LOW_flash": 0.9,
    "L1_HIGH_flash": 0.8,
    "L5_LOW_flash": 0.9,
    "L5_HIGH_flash": 0.4, # Prefer Pro
    "L5_HIGH_pro": 0.9
}

def load_weights():
    if os.path.exists(WEIGHTS_FILE):
        try:
            with open(WEIGHTS_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return DEFAULT_WEIGHTS.copy()

def save_weights(weights):
    with open(WEIGHTS_FILE, 'w') as f:
        json.dump(weights, f, indent=2)

def run_learning_cycle():
    """
    Nightly: Analyze routing success and update weights.
    """
    logger.info("🧠 Starting Self-Learning Cycle...")
    
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Fetch Events (last 24h)
    # Ideally join with Audit Logs. For now, we assume auditor_score is updated in routing_events 
    # (or we join manually). 
    # Let's simplify: Auditor updates routing_events table directly if possible, or we join here.
    
    # Simple join query (assuming timestamps match roughly or via ID if we had it)
    # We will assume audit logs are key.
    
    query = """
    SELECT 
        r.life_level, r.complexity, r.model_selected,
        a.efficiency_score, r.cost_est
    FROM routing_events r
    JOIN audit_logs a ON r.user_id = a.user_id AND r.response = a.response -- heuristic join
    WHERE r.timestamp > datetime('now', '-1 day')
    """
    # Since we didn't strictly link IDs in previous steps (telemetry ID vs Audit ID),
    # we might need to rely on the fact that we can just analyse general trends provided explicitly.
    # For this MVP, let's look at audit_logs purely mapped to model_used.
    
    df = pd.read_sql_query("SELECT model_used, efficiency_score, query FROM audit_logs", conn)
    conn.close()
    
    if df.empty:
        logger.info("ℹ️ No data to learn from.")
        return

    weights = load_weights()
    current_weights = weights.copy()
    
    # Logic: Group by Model (and ideally context/level)
    # We lack strict Level in AuditLogs, so we trust generalized model performance.
    
    # E.g. If 'gemini-2.5-flash' has avg score > 8, boost its usage for High Complexity.
    
    for model_name, group in df.groupby('model_used'):
        avg_score = group['efficiency_score'].mean()
        logger.info(f"📊 Model {model_name}: Avg Score {avg_score:.1f}")
        
        # Determine "Flash" vs "Pro" mapping for keys
        m_key = "flash" if "flash" in model_name.lower() else "pro"
        
        if avg_score >= 8.0:
            # Reward: Boost availability
            # E.g. L5_HIGH_flash += 0.05 (If flash is good, use it more)
            change = 0.05
        elif avg_score <= 5.0:
            # Penalty
            change = -0.05
        else:
            change = 0
            
        if change != 0:
            for k in current_weights:
                if m_key in k:
                    current_weights[k] = min(1.0, max(0.1, current_weights[k] + change))
                    logger.info(f"⚖️ Adjusted {k}: {weights[k]} -> {current_weights[k]}")

    save_weights(current_weights)
    logger.info("✅ Learning Cycle Complete. Weights updated.")
