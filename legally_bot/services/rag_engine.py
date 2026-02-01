import logging
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
# from rank_bm25 import BM25Okapi # Optional: Keep commented if not using BM25 yet or uncomment if implementing hybrid
from legally_bot.config import settings

class RAGEngine:
    def __init__(self):
        try:
            self.api_key = settings.PINECONE_API_KEY
            self.environment = settings.PINECONE_ENV
            self.encoder = SentenceTransformer('BAAI/bge-large-en-v1.5')
            self.pc = Pinecone(api_key=self.api_key)
            self.index = self.pc.Index(settings.PINECONE_INDEX_NAME)
            logging.info("✅ RAG Engine initialized (Real Mode)")
        except Exception as e:
            logging.error(f"❌ Failed to init RAG Engine: {e}")
            self.index = None

    async def search(self, query: str):
        if not self.index:
            logging.warning("RAG Index not available, returning answer.")
            return {"answer": "Search currently unavailable (DB connection failed).", "source_documents": []}

        try:
            logging.info(f"🔎 Searching for: {query}")
            
            # 1. Generate embedding
            # encode() returns numpy array, convert to list for Pinecone
            vector = self.encoder.encode(query).tolist()
            
            # 2. Pinecone search
            results = self.index.query(vector=vector, top_k=3, include_metadata=True)
            
            # 3. Format results
            matches = results.get('matches', [])
            source_docs = []
            context_text = ""
            
            for match in matches:
                metadata = match.get('metadata', {})
                text = metadata.get('text', 'No text')
                title = metadata.get('title', 'Unknown Source')
                score = match.get('score', 0.0)
                
                source_docs.append({"title": title, "content": text, "score": score})
                context_text += f"-- Source: {title} --\n{text}\n\n"

            # 4. Generate Answer (Here we would call an LLM like GPT/Gemini with the context)
            # For this step, since we don't have an LLM configured in the prompt requirements yet,
            # we will return the context as the "answer" or a placeholder saying "Here is what I found".
            
            answer = f"Found {len(matches)} relevant documents.\n\nHere is the retrieved context:\n{context_text[:500]}..." # Truncated for display
            
            return {
                "answer": answer,
                "source_documents": source_docs
            }

        except Exception as e:
            logging.error(f"Search failed: {e}", exc_info=True)
            return {"answer": "Error during search.", "source_documents": []}
