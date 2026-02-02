
import logging
import functools
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure simple retry decorator
# Retries 3 times with exponential backoff for network/IO errors
def with_retry(attempts=3):
    def decorator(func):
        @functools.wraps(func)
        @retry(
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True
        )
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logging.warning(f"⚠️ Function {func.__name__} failed: {e}. Retrying...")
                raise e
        return wrapper
    return decorator

class VectorDBFallback:
    """
    Manages fallback between Pinecone (Primary) and ChromaDB (Secondary).
    """
    def __init__(self):
        self.chroma_client = None
        self.chroma_collection = None
        self._initialized = False

    def init_chroma(self):
        """Lazy init of ChromaDB"""
        if self._initialized:
            return
        try:
            import chromadb
            # Use persistent client locally for fallback
            self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
            self.chroma_collection = self.chroma_client.get_or_create_collection(name="legally_fallback")
            self._initialized = True
            logging.info("✅ ChromaDB Fallback initialized.")
        except Exception as e:
            logging.error(f"❌ Failed to init ChromaDB: {e}")

    async def upsert_fallback(self, vectors):
        """Upsert to Chroma if Pinecone fails"""
        self.init_chroma()
        if not self.chroma_collection:
            return
        
        try:
            ids = [v[0] for v in vectors]
            embeddings = [v[1] for v in vectors]
            metadatas = [v[2] for v in vectors]
            
            self.chroma_collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas
            )
            logging.info(f"Saved {len(ids)} vectors to ChromaDB (Fallback).")
        except Exception as e:
            logging.error(f"ChromaDB upsert failed: {e}")

resilience_manager = VectorDBFallback()
