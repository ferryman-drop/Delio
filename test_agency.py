import unittest
import os
import sqlite3
import task_manager
import calendar_manager
from datetime import datetime, timedelta

class TestAgency(unittest.TestCase):
    def setUp(self):
        # Use a temporary in-memory DB or mock the global connection
        # Since the system uses `memory_manager.global_memory`, we should ideally mock `get_connection`
        pass

    def test_ics_generation(self):
        print("\n📅 Testing Calendar (ICS Generation)...")
        cm = calendar_manager.calendar_system
        
        # Test Generation
        res = cm._generate_ics("Test Meeting", "2023-10-31T18:00:00", 60)
        print(f"Result: {res}")
        
        self.assertIn("VCALENDAR", str(res))
        
        # Extract filename
        import re
        match = re.search(r"(/tmp/event_.*\.ics)", res)
        if match:
            filename = match.group(1)
            print(f"File created: {filename}")
            self.assertTrue(os.path.exists(filename))
            os.remove(filename) # Cleanup
            print("✅ ICS Verification Passed")

if __name__ == '__main__':
    unittest.main()
