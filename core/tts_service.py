
import edge_tts
import uuid
import os
import logging

logger = logging.getLogger("Delio.TTS")

class TTSService:
    def __init__(self):
        # Voices: uk-UA-OstapNeural (Male), uk-UA-PolinaNeural (Female)
        self.voice = "uk-UA-OstapNeural" 
        self.output_dir = "/tmp/audio_buffer"
        os.makedirs(self.output_dir, exist_ok=True)
        
    async def generate_speech(self, text: str) -> str:
        """Generates MP3 from text. Returns path."""
        try:
            # Clean markdown for better speech
            clean_text = text.replace("*", "").replace("_", "").replace("`", "")
            
            communicate = edge_tts.Communicate(clean_text, self.voice)
            filename = f"{self.output_dir}/speech_{uuid.uuid4()}.mp3"
            await communicate.save(filename)
            logger.info(f"🎙️ Audio generated: {filename}")
            return filename
        except Exception as e:
            logger.error(f"TTS Error: {e}")
            return None

# Singleton
tts = TTSService()
