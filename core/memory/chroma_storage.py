import chromadb
import logging
import asyncio
import uuid
from typing import List, Optional
from datetime import datetime
import os
import config

# We need a wrapper to run synchronous Chroma calls in a threadpool
# until Chroma releases a full native async client (it's partial currently)

logger = logging.getLogger("Delio.Memory.Chroma")

class ChromaManager:
    def __init__(self, db_path: str = "data/chroma_db"):
        self.db_path = db_path
        self.client = None
        self.collection = None

    def _init_sync(self):
        """Synchronous initialization"""
        try:
            os.makedirs(self.db_path, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.db_path)
            self.collection = self.client.get_or_create_collection(
                name="delio_memories",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"✅ ChromaDB initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"❌ ChromaDB init failed: {e}")

    async def init_db(self):
        """Async wrapper for initialization"""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._init_sync)

    def _get_embedding_sync(self, text: str, task_type: str = "retrieval_document") -> List[float]:
        """Calls Gemini API for embedding (Sync wrapper)"""
        try:
            if not text: return []
            
            # Use Google GenAI SDK
            from google import genai
            client = genai.Client(api_key=config.GEMINI_KEY)
            
            result = client.models.embed_content(
                model="models/gemini-embedding-001",
                contents=text,
                config={'task_type': task_type.upper()}
            )
            return result.embeddings[0].values
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return []

    async def store_memory(self, user_id: int, text: str, metadata: dict = None):
        """Store a semantic memory"""
        if not self.collection: return
        
        if metadata is None: metadata = {}
        metadata["user_id"] = user_id
        metadata["timestamp"] = datetime.now().isoformat()
        
        def _do_store():
            emb = self._get_embedding_sync(text, "retrieval_document")
            if not emb: return False
            
            self.collection.add(
                documents=[text],
                embeddings=[emb],
                metadatas=[metadata],
                ids=[str(uuid.uuid4())]
            )
            return True

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _do_store)

    async def search(self, user_id: int, query: str, limit: int = 5) -> List[str]:
        """Semantic search"""
        if not self.collection: return []

        def _do_search():
            emb = self._get_embedding_sync(query, "retrieval_query")
            if not emb: return []
            
            results = self.collection.query(
                query_embeddings=[emb],
                n_results=limit,
                where={"user_id": user_id}
            )
            
            if results and results['documents']:
                return [doc for doc in results['documents'][0] if doc]
            return []

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _do_search)
