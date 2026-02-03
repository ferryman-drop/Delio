import unittest
from unittest.mock import patch, AsyncMock
import old_core as core
import router

class TestModelSwitch(unittest.IsolatedAsyncioTestCase):
    async def test_router_switching(self):
        print("🧪 Testing Router -> Model Switch...")
        
        # Mock Redis
        with patch('core.get_cached_context', return_value=[]):
            with patch('core.cache_context'):
                # Mock Memory
                with patch('memory_manager.global_memory.get_profile_text', return_value="Verified User"):
                    
                    # CASE 1: Router says "Pro" (High Level/Complexity)
                    with patch('router.DeepSeekRouter.route_request') as mock_route:
                        mock_route.return_value = {
                            "internal_model": "pro",
                            "life_level": "L7",
                            "compressed_context": "Context"
                        }
                        
                        # Mock LLM Call
                        with patch('core.call_llm_agentic', new_callable=AsyncMock) as mock_llm:
                            mock_llm.return_value = ("Response", "gemini-1.5-pro")
                            
                            mock_msg = AsyncMock()
                            mock_msg.from_user.id = 123
                            mock_msg.text = "Complex strategy question"
                            
                            await core.process_ai_request(mock_msg, "Complex strategy question")
                            
                            # Verify call args
                            args, _ = mock_llm.call_args
                            # preferred arg is at index 3
                            preferred_model = args[3]
                            print(f"CASE 1 (Pro): Router said Pro -> Core called {preferred_model}")
                            self.assertEqual(preferred_model, 'gemini-pro')

                    # CASE 2: Router says "Flash" (Low Complexity)
                    with patch('router.DeepSeekRouter.route_request') as mock_route:
                        mock_route.return_value = {
                            "internal_model": "flash_3",
                            "life_level": "L2",
                        }
                        
                        with patch('core.call_llm_agentic', new_callable=AsyncMock) as mock_llm:
                            mock_llm.return_value = ("Response", "gemini-2.5-flash")
                            
                            await core.process_ai_request(mock_msg, "Simple question")
                            
                            args, _ = mock_llm.call_args
                            preferred_model = args[3]
                            print(f"CASE 2 (Flash): Router said Flash -> Core called {preferred_model}")
                            self.assertEqual(preferred_model, 'gemini-flash')

if __name__ == '__main__':
    unittest.main()
