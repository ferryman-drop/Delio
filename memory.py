
import os
import logging
import chromadb
# from chromadb.utils import embedding_functions # Not using automatic embedding function
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
CHROMA_PATH = os.path.join(os.getcwd(), "data", "chroma_db")
COLLECTION_NAME = "chat_history"
NOTES_COLLECTION_NAME = "user_notes"

# Initialize global variables
chroma_client = None
collection = None
notes_collection = None

def get_embedding(text: str, task_type: str = "retrieval_document") -> list[float]:
    """Generate embedding using Gemini with specific task type (New SDK)"""
    try:
        # Check if text is valid
        if not text or not isinstance(text, str):
            logger.warning("⚠️ Empty text for embedding")
            return []
        
        # New SDK
        import config
        from google import genai
        client = genai.Client(api_key=config.GEMINI_KEY)
        
        # New SDK: client.models.embed_content
        result = client.models.embed_content(
            model="text-embedding-004",
            contents=text
        )
        # Result structure: result.embeddings[0].values (list of floats)
        return result.embeddings[0].values
    except Exception as e:
        logger.error(f"❌ Embedding error ({task_type}): {e}")
        return []

def init_memory():
    """Initialize ChromaDB client and collection"""
    global chroma_client, collection
    try:
        if not os.path.exists(CHROMA_PATH):
            os.makedirs(CHROMA_PATH, exist_ok=True)
            
        chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        
        # We handle embeddings manually to support task_type
        # If collection exists, get it. If not, create it.
        collection = chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        notes_collection = chroma_client.get_or_create_collection(
            name=NOTES_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"✅ ChromaDB initialized at {CHROMA_PATH}")
    except Exception as e:
        logger.error(f"❌ Failed to init ChromaDB: {e}")

def save_interaction(user_id: int, user_input: str, bot_response: str, model_used: str):
    """Save user input and bot response as separate documents"""
    if collection is None:
        return

    try:
        timestamp = datetime.now().isoformat()
        
        # 1. User Input
        emb_user = get_embedding(user_input, "retrieval_document")
        if emb_user:
            collection.add(
                documents=[user_input],
                embeddings=[emb_user],
                metadatas=[{
                    "user_id": user_id, 
                    "role": "user", 
                    "timestamp": timestamp,
                    "model": model_used
                }],
                ids=[f"user_{uuid.uuid4()}"]
            )
        
        # 2. Bot Response
        emb_bot = get_embedding(bot_response, "retrieval_document")
        if emb_bot:
            collection.add(
                documents=[bot_response],
                embeddings=[emb_bot],
                metadatas=[{
                    "user_id": user_id, 
                    "role": "assistant", 
                    "timestamp": timestamp,
                    "model": model_used
                }],
                ids=[f"bot_{uuid.uuid4()}"]
            )
            
        logger.info(f"💾 Saved interaction to memory for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Failed to save memory: {e}")

def search_memory(user_id: int, query: str, limit: int = 5) -> list[str]:
    """Retrieve relevant context from memory"""
    if collection is None:
        return []

    try:
        # Generate query embedding
        emb_query = get_embedding(query, "retrieval_query")
        if not emb_query:
            return []

        results = collection.query(
            query_embeddings=[emb_query],
            n_results=limit,
            where={"user_id": user_id}
        )
        
        if results and results['documents']:
            found_docs = results['documents'][0]
            valid_docs = [doc for doc in found_docs if doc]
            if valid_docs:
                logger.info(f"🔍 Retrieved {len(valid_docs)} memories")
            return valid_docs
            
        return []
    except Exception as e:
        logger.error(f"❌ Memory search error: {e}")
        return []

def save_note(user_id: int, content: str, topic: str = "general"):
    """Зберегти важливу нотатку користувача"""
    if notes_collection is None:
        init_memory()
    
    try:
        timestamp = datetime.now().isoformat()
        emb = get_embedding(content, "retrieval_document")
        if emb:
            notes_collection.add(
                documents=[content],
                embeddings=[emb],
                metadatas=[{
                    "user_id": user_id,
                    "topic": topic,
                    "timestamp": timestamp,
                    "type": "note"
                }],
                ids=[f"note_{uuid.uuid4()}"]
            )
            logger.info(f"📌 Saved note for user {user_id}")
            return True
    except Exception as e:
        logger.error(f"❌ Failed to save note: {e}")
    return False

def search_notes(user_id: int, query: str, limit: int = 3) -> list[str]:
    """Пошук серед нотаток користувача"""
    if notes_collection is None:
        return []

    try:
        emb_query = get_embedding(query, "retrieval_query")
        if not emb_query:
            return []

        results = notes_collection.query(
            query_embeddings=[emb_query],
            n_results=limit,
            where={"user_id": user_id}
        )
        
        if results and results['documents']:
            return [doc for doc in results['documents'][0] if doc]
    except Exception as e:
        logger.error(f"❌ Note search error: {e}")
    return []

def get_notes_stats(user_id: int):
    """Отримати статистику нотаток користувача"""
    if notes_collection is None:
        return {"count": 0, "topics": []}
    
    try:
        results = notes_collection.get(
            where={"user_id": user_id},
            include=["metadatas"]
        )
        
        if not results or not results['metadatas']:
            return {"count": 0, "topics": []}
            
        count = len(results['metadatas'])
        topics = list(set([m.get("topic", "general") for m in results['metadatas']]))
        
        return {
            "count": count,
            "topics": topics[:5] # Повертаємо топ-5 тем
        }
    except Exception as e:
        logger.error(f"❌ Error getting notes stats: {e}")
        return {"count": 0, "topics": []}
