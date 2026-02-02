import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import sqlite3
import digest_manager
import memory_manager

class TestFractalMemory(unittest.IsolatedAsyncioTestCase):
    async def test_daily_digest_flow(self):
        print("🧠 Testing Fractal Memory (Daily Digest)...")
        
        # MOCK Gemini response
        with patch('google.generativeai.GenerativeModel') as mock_model_cls:
            mock_model = MagicMock()
            mock_model_cls.return_value = mock_model
            
            # Mock successful JSON response
            mock_resp = MagicMock()
            mock_resp.text = '{"narrative": "Today was productive.", "mood_score": 8, "key_topics": ["coding"]}'
            mock_model.generate_content.return_value = mock_resp
            
            # Mock DB fetch (ensure it returns some rows so logic runs)
            with patch('sqlite3.connect') as mock_sql:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_sql.return_value = mock_conn
                mock_conn.cursor.return_value = mock_cursor
                
                rows = [('Hello', 'Hi', '2023-10-01 10:00:00')]
                mock_cursor.fetchall.return_value = rows
                
                # EXECUTE
                # Inject mock mem_ctrl connection for saving
                with patch.object(digest_manager.digest_system.mem_ctrl, 'get_connection') as mock_mem_conn:
                     mock_dest_conn = MagicMock()
                     mock_mem_conn.return_value = mock_dest_conn
                     
                     res = await digest_manager.digest_system.generate_daily_digest(123)
                     
                     # VERIFY
                     print(f"✅ Generated Digest: {res}")
                     self.assertIsNotNone(res)
                     self.assertEqual(res['mood_score'], 8)
                     
                     # Check INSERT called
                     mock_dest_conn.execute.assert_called()
                     print("✅ Digest Saved to DB.")

if __name__ == '__main__':
    unittest.main()
