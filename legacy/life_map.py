import sqlite3
import pandas as pd
import memory_manager
from enum import Enum

class LifeLevel(Enum):
    L1 = "L1: Survival"
    L2 = "L2: Stability"
    L3 = "L3: Professional"
    L4 = "L4: Leader"
    L5 = "L5: Architect"
    L6 = "L6: Owner"
    L7 = "L7: Meta / Freedom"

class LifeCalculator:
    def __init__(self):
        self.mem_ctrl = memory_manager.MemoryController()

    def get_user_stats(self, user_id):
        conn = self.mem_ctrl.get_connection()
        
        # 1. Decisions
        decisions_df = pd.read_sql_query(
            "SELECT * FROM strategic_decisions WHERE user_id = ?",
            conn, params=(user_id,)
        )
        
        # 2. Insights
        insights_df = pd.read_sql_query(
            "SELECT * FROM strategic_insights WHERE user_id = ?",
            conn, params=(user_id,)
        )
        
        conn.close()
        
        n_decisions = len(decisions_df)
        n_insights = len(insights_df)
        
        # XP Calculation
        # Simple Logic: 10 XP per Decision, 5 XP per Insight
        total_xp = (n_decisions * 10) + (n_insights * 5)
        
        # Level Logic (Exponential-ish)
        level = LifeLevel.L1
        if total_xp > 50: level = LifeLevel.L2
        if total_xp > 150: level = LifeLevel.L3
        if total_xp > 400: level = LifeLevel.L4
        if total_xp > 1000: level = LifeLevel.L5
        if total_xp > 2500: level = LifeLevel.L6
        if total_xp > 5000: level = LifeLevel.L7
        
        return {
            "level": level.value,
            "xp": total_xp,
            "decisions_count": n_decisions,
            "insights_count": n_insights,
            "decisions_df": decisions_df,
            "insights_df": insights_df
        }

    def get_system_health(self):
        """Get Audit Logs for Dashboard"""
        conn = self.mem_ctrl.get_connection()
        try:
            audit_df = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY date DESC LIMIT 100", conn)
        except:
            audit_df = pd.DataFrame()
        conn.close()
        return audit_df

    def get_pricing_stats(self):
        """Get Telemetry Data"""
        conn = self.mem_ctrl.get_connection()
        try:
            df = pd.read_sql_query("SELECT * FROM routing_events ORDER BY timestamp DESC LIMIT 500", conn)
        except:
            df = pd.DataFrame()
        conn.close()
        return df
