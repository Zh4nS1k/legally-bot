import logging
import json
import requests
import google.generativeai as genai
from groq import Groq
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
from legally_bot.config import settings

class RAGEngine:
    def __init__(self):
        try:
            self.api_key = settings.PINECONE_API_KEY
            self.environment = settings.PINECONE_ENV
            self.encoder = SentenceTransformer('BAAI/bge-large-en-v1.5')
            self.pc = Pinecone(api_key=self.api_key)
            self.index = self.pc.Index(settings.PINECONE_INDEX_NAME)
            
            # Init LLM clients
            genai.configure(api_key=settings.GEMINI_API_KEY)
            # We initialize the model later with specific versions to avoid 404
            self.groq_client = None
            if settings.GROQ_API_KEY:
                try:
                    self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
                except Exception as ge:
                    logging.error(f"Failed to init Groq client: {ge}")
            
            logging.info("✅ RAG Engine initialized (Pinecone + Multi-LLM Fallback)")
        except Exception as e:
            logging.error(f"❌ Failed to init RAG Engine: {e}")
            self.index = None

    async def _try_deepseek(self, prompt: str):
        if not settings.OPENROUTER_API_KEY:
            raise ValueError("OpenRouter API key not configured")
        
        logging.info("Attempting DeepSeek via OpenRouter...")
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": "deepseek/deepseek-r1",
                "messages": [{"role": "user", "content": prompt}]
            }),
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        if 'choices' not in data:
            logging.error(f"OpenRouter Error Response: {data}")
            raise ValueError(f"OpenRouter response missing 'choices': {data.get('error', 'Unknown error')}")
        return data['choices'][0]['message']['content']

    async def _try_gemini(self, prompt: str):
        logging.info("Attempting Gemini...")
        # Try a few variants to ensure success
        model_names = ['gemini-2.0-flash-exp', 'gemini-1.5-flash', 'gemini-3-flash-preview']
        last_err = None
        for name in model_names:
            try:
                logging.info(f"Trying Gemini model: {name}")
                model = genai.GenerativeModel(name)
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                last_err = e
                logging.warning(f"Gemini {name} failed: {e}")
                continue
        raise last_err

    async def _try_groq(self, prompt: str):
        if not self.groq_client:
            raise ValueError("Groq API key not configured")
        
        logging.info("Attempting Llama 3.3 via Groq...")
        completion = self.groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            max_completion_tokens=1024,
            top_p=1,
            stream=False # Not using stream for easier fallback logic
        )
        return completion.choices[0].message.content

    async def search(self, query: str, num_chunks: int = 3, num_articles: int = 3, lang: str = "ru"):
        if not self.index:
            logging.warning("RAG Index not available.")
            return {"answer": "Search currently unavailable.", "chunks": [], "articles": []}

        try:
            logging.info(f"🔎 Searching for: {query}")
            
            vector = self.encoder.encode(query).tolist()
            # Retrieve enough documents to satisfy the maximum possible requirement (5 chunks + 5 articles = 10)
            results = self.index.query(vector=vector, top_k=15, include_metadata=True)
            
            matches = results.get('matches', [])
            chunks = []
            articles = []
            
            for match in matches:
                metadata = match.get('metadata', {})
                text = metadata.get('text', 'No text')
                title = metadata.get('title', 'Unknown Source')
                score = match.get('score', 0.0)
                doc_type = metadata.get('type', 'chunk')

                doc_info = {"title": title, "content": text, "score": score, "type": doc_type}
                
                if doc_type == 'article' and len(articles) < num_articles:
                    articles.append(doc_info)
                elif doc_type != 'article' and len(chunks) < num_chunks:
                    chunks.append(doc_info)
            
            # Fill with any matches if we didn't get enough specific types
            if len(chunks) < num_chunks or len(articles) < num_articles:
                for match in matches:
                    metadata = match.get('metadata', {})
                    doc_info = {
                        "title": metadata.get('title', 'Unknown Source'),
                        "content": metadata.get('text', 'No text'),
                        "score": match.get('score', 0.0),
                        "type": metadata.get('type', 'chunk')
                    }
                    if doc_info in chunks or doc_info in articles:
                        continue
                        
                    if len(chunks) < num_chunks:
                        chunks.append(doc_info)
                    elif len(articles) < num_articles:
                        articles.append(doc_info)

            context_text = "\n\n".join([f"Source: {d['title']}\nContent: {d['content']}" for d in chunks + articles])
            
            lang_instruction = "Respond in Russian." if lang == "ru" else "Respond in English."
            
            prompt = f"""
            You are an AI assistant specializing in Kazakhstan Law. 
            Use the following context to answer the user's question accurately.
            {lang_instruction}
            If the context doesn't contain the answer, say you don't know based on the provided documents, but try to be helpful.
            
            Context:
            {context_text}
            
            Question: {query}
            
            Answer:
            """
            
            # --- Fallback Logic ---
            answer = None
            errors = []
            
            # 1. DeepSeek
            try:
                answer = await self._try_deepseek(prompt)
            except Exception as e:
                errors.append(f"DeepSeek failed: {e}")
                logging.warning(errors[-1])
            
            # 2. Gemini
            if not answer:
                try:
                    answer = await self._try_gemini(prompt)
                except Exception as e:
                    errors.append(f"Gemini failed: {e}")
                    logging.warning(errors[-1])
            
            # 3. Groq
            if not answer:
                try:
                    answer = await self._try_groq(prompt)
                except Exception as e:
                    errors.append(f"Groq failed: {e}")
                    logging.warning(errors[-1])
            
            if not answer:
                error_summary = " | ".join(errors)
                logging.error(f"All LLM providers failed: {error_summary}")
                return {"answer": "⚠️ All AI providers are currently unavailable. Please try again later.", "chunks": [], "articles": []}
            
            return {
                "answer": answer,
                "chunks": chunks[:num_chunks],
                "articles": articles[:num_articles]
            }

        except Exception as e:
            logging.error(f"Search overall failed: {e}", exc_info=True)
            return {"answer": "Error during search.", "chunks": [], "articles": []}
