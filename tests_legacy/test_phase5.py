import unittest
import os
import json
import sqlite3
import pandas as pd
from unittest.mock import MagicMock, patch

import telemetry
import routing_learner
import memory_manager

class TestPhase5(unittest.TestCase):
    def setUp(self):
        # Use simple DB interaction
        self.user_id = 777
        self.conn = memory_manager.MemoryController().get_connection()
        
    def tearDown(self):
        # Clean up
        self.conn.execute("DELETE FROM routing_events WHERE user_id=?", (self.user_id,))
        self.conn.commit()
        self.conn.close()

    def test_telemetry_flow(self):
        print("🧪 Testing Telemetry Logging...")
        # 1. Log Event
        cost = telemetry.log_routing_event(
            self.user_id, "L3", "High", "gemini-1.5-flash", 
            "Input text "*10, "Output text "*20
        )
        self.assertGreater(cost, 0.0)
        
        # 2. Verify DB
        row = self.conn.execute("SELECT * FROM routing_events WHERE user_id=? LIMIT 1", (self.user_id,)).fetchone()
        self.assertIsNotNone(row)
        print("✅ Telemetry Logged Successfully")
        
    def test_learner_logic(self):
        print("🧠 Testing Learner Logic...")
        # 1. Mock Dataframe return for run_learning_cycle
        # We simulate that 'flash' performed POORLY (Score 3.0)
        
        mock_df = pd.DataFrame({
            "model_used": ["gemini-1.5-flash", "gemini-1.5-flash"],
            "efficiency_score": [3.0, 4.0],
            "query": ["q1", "q2"]
        })
        
        with patch('pandas.read_sql_query', return_value=mock_df):
            # Load initial weights
            initial_w = routing_learner.load_weights()
            flash_key = "L5_HIGH_flash" # We know this key exists in defaults
            initial_val = initial_w.get(flash_key, 0.5)
            
            # Run Cycle
            routing_learner.run_learning_cycle()
            
            # Check updated weights
            new_w = routing_learner.load_weights()
            new_val = new_w.get(flash_key)
            
            print(f"📉 Weight Change: {initial_val} -> {new_val}")
            
            # Should have decreased because score < 5.0
            # Although our learner logic groups by model name containing 'flash', so it affects all flash keys
            self.assertLess(new_val, initial_val)
            print("✅ Learner Adjusted Weights Correctly")

if __name__ == '__main__':
    unittest.main()
