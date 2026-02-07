import sys
import os
# Add root to python path to find config
sys.path.append("/root/ai_assistant")

import time
import logging
import chromadb
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from google import genai
from config import GEMINI_KEY, MODEL_FAST

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/root/ai_assistant/logs/obsidian_sync.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Delio.ObsidianSync")

# Config
OBSIDIAN_PATH = "/data/obsidian"
CHROMA_PATH = "/root/ai_assistant/data/chroma_db"
COLLECTION_NAME = "obsidian_knowledge"

class ObsidianHandler(FileSystemEventHandler):
    def __init__(self, chroma_client, gemini_client):
        self.collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
        self.gemini = gemini_client
        self.last_processed = {} # path -> timestamp (for debounce)

    def _get_embedding(self, text):
        models_to_try = ["models/gemini-embedding-001"]
        
        for model in models_to_try:
            try:
                # Use Gemini for embeddings
                result = self.gemini.models.embed_content(
                    model=model,
                    contents=text,
                    config={
                        'task_type': 'RETRIEVAL_DOCUMENT'
                    }
                )
                return result.embeddings[0].values
            except Exception as e:
                logger.warning(f"Embedding failed with {model}: {e}")
        
        logger.error("All embedding models failed.")
        return None

    def _process_file(self, file_path):
        # 1. Debounce (2 seconds)
        now = time.time()
        if file_path in self.last_processed:
            if now - self.last_processed[file_path] < 2:
                return

        if not file_path.endswith(".md"):
            return

        logger.info(f"📄 Processing: {file_path}")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                return

            # Chunking (Simple max chars)
            # For V1, we just take the first 8000 chars aka "The Abstract"
            # Ideally -> split by headers
            truncated_content = content[:8000]

            embedding = self._get_embedding(truncated_content)
            
            if embedding:
                # ID = filename
                file_id = os.path.basename(file_path)
                
                self.collection.upsert(
                    ids=[file_id],
                    documents=[truncated_content],
                    embeddings=[embedding],
                    metadatas=[{"path": file_path, "last_modified": str(now)}]
                )
                logger.info(f"✅ Indexed: {file_id}")
                self.last_processed[file_path] = now

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")

    def on_modified(self, event):
        if not event.is_directory:
            self._process_file(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self._process_file(event.src_path)

def main():
    # Ensure dirs
    os.makedirs(OBSIDIAN_PATH, exist_ok=True)
    os.makedirs(os.path.dirname(CHROMA_PATH), exist_ok=True)

    # Init Clients
    logger.info("🔌 Connecting to ChromaDB...")
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    logger.info("🔌 Connecting to Gemini...")
    gemini_client = genai.Client(api_key=GEMINI_KEY)

    # Setup Watchdog
    event_handler = ObsidianHandler(chroma_client, gemini_client)
    observer = Observer()
    observer.schedule(event_handler, OBSIDIAN_PATH, recursive=True)
    
    logger.info(f"👁️ Obsidian Watcher started on {OBSIDIAN_PATH}. Initial scan incoming...")
    
    # Initial Scan
    for root, dirs, files in os.walk(OBSIDIAN_PATH):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                event_handler._process_file(file_path)
    
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    # Add root to python path to find config
    import sys
    sys.path.append("/root/ai_assistant")
    main()
