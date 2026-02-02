import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import core
import asyncio

class TestVoicePipeline(unittest.IsolatedAsyncioTestCase):
    async def test_full_pipeline(self):
        print("🎤 Testing Voice Pipeline (Mocked)...")
        
        # MOCK 1: Gemini Transcription
        with patch('google.generativeai.upload_file') as mock_upload:
            with patch('google.generativeai.GenerativeModel') as mock_genai_cls:
                mock_model = MagicMock()
                mock_genai_cls.return_value = mock_model
                
                # Transcription Result
                mock_model.generate_content.return_value.text = "Umm, hello there. I want to errr create a new project."
                
                # MOCK 2: DeepSeek Refinement
                with patch('core.deep_client.chat.completions.create') as mock_deepseek:
                    mock_deepseek.return_value.choices = [
                        MagicMock(message=MagicMock(content="🎯 THESIS: User wants to create a new project."))
                    ]
                    
                    # MOCK 3: Agent Execution (Stop it from actually running LLM)
                    with patch('core.process_ai_request', new_callable=AsyncMock) as mock_process:
                        
                        # EXECUTE
                        mock_msg = AsyncMock()
                        mock_msg.from_user.id = 123
                        await core.process_voice_message(mock_msg, "/tmp/test.ogg")
                        
                        # VERIFY 1: Transcription called?
                        mock_model.generate_content.assert_called()
                        print("✅ Transcription Step: OK")
                        
                        # VERIFY 2: DeepSeek Refinement called?
                        mock_deepseek.assert_called()
                        print("✅ Refinement Step: OK")
                        
                        # VERIFY 3: Did we pass the REFINED text to the agent?
                        args, _ = mock_process.call_args
                        # args[1] is the text
                        passed_text = args[1]
                        print(f"📝 Text pushed to Agent: '{passed_text}'")
                        self.assertIn("THESIS", passed_text)
                        print("✅ Pipeline Success: Refined text reached Agent.")

if __name__ == '__main__':
    unittest.main()
