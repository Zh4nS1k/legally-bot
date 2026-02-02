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
                references = metadata.get('references', [])

                doc_info = {
                    "title": title, 
                    "content": text, 
                    "score": score, 
                    "type": doc_type,
                    "article": metadata.get('article'),
                    "url": metadata.get('url'),
                    "references": references
                }
                
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

            # Graph Expansion (Dijkstra-ish)
            expanded_results = await self._expand_context(chunks, articles)
            chunks = expanded_results['chunks']
            articles = expanded_results['articles']

            context_text = ""
            for d in chunks + articles:
                context_text += f"---\nSource: {d.get('title', 'Unknown')}\n"
                context_text += f"Article: {d.get('article', 'N/A')}\n"
                context_text += f"URL: {d.get('url', 'N/A')}\n"
                context_text += f"Content: {d['content']}\n"
            
            lang_instruction = "Respond in Russian." if lang == "ru" else "Respond in English."
            
            # Reasoning Chain (Markov-ish)
            # Step 1: Draft
            draft_prompt = f"""
            You are an AI assistant specialized in Kazakhstan Law.
            Strictly analyze the provided context to answer the user's question.
            
            Context:
            {context_text}
            
            Question: {query}
            
            Draft a preliminary answer based ONLY on the context. Cite sources.
            """
            
            draft_answer = await self._generate_with_fallback(draft_prompt)
            
            # Step 2: Refine (Transition)
            final_prompt = f"""
            You are a Senior Legal Editor. Review the draft answer against the context.
            
            Context:
            {context_text}
            
            Draft Answer:
            {draft_answer}
            
            User Question: {query}
            
            Instructions:
            1. Verify all citations exist in the context.
            2. Remove any hallucinated details.
            3. Ensure the tone is professional.
            4. {lang_instruction}
            
            Final Answer:
            """
            
            final_answer = await self._generate_with_fallback(final_prompt)
            
            return {
                "answer": final_answer,
                "chunks": chunks[:num_chunks],
                "articles": articles[:num_articles]
            }

        except Exception as e:
            logging.error(f"Search overall failed: {e}", exc_info=True)
            return {"answer": "Error during search.", "chunks": [], "articles": []}

    async def _expand_context(self, chunks: list, articles: list):
        """
        Graph Traversal: Analyzes 'references' metadata in retrieved chunks 
        and fetches the cited articles to expand context.
        """
        referenced_articles = []
        for doc in chunks + articles:
            # Check if this document has references
            # In search(), we need to make sure we extracted 'references' from metadata
            refs = doc.get("references", [])
            referenced_articles.extend(refs) # Add IDs
            
        referenced_articles = list(set(referenced_articles)) # Unique
        
        if not referenced_articles:
            return {"chunks": chunks, "articles": articles}
            
        logging.info(f"🔗 Graph Traversal: Found references to articles {referenced_articles}")
        
        # Traverse Graph: Fetch these specific articles
        # This requires a new search or fetch operation.
        # Since we stored 'article' in metadata, we can filter for it.
        
        try:
            # We can't do a massive OR filter in one go specific to `article` IN list easily with vector search metadata filter 
            # if the list is huge, but for a few it's fine.
            # $in is supported.
            
            filter_query = {
                "article": {"$in": referenced_articles},
                "type": "article"
            }
            
            # Semantic search is less relevant here, we want exact matches.
            # But Pinecone query usually requires a vector.
            # We can use a dummy vector (all zeros) or just query with a generic law vector.
            # OR fetch by ID if we knew the vector IDs. We don't.
            # We will use a dummy query with filter.
            
            dummy_vector = [0.0] * 1024 # BGE-Large dimension is 1024
            
            results = self.index.query(
                vector=dummy_vector,
                filter=filter_query,
                top_k=len(referenced_articles),
                include_metadata=True
            )
            
            matches = results.get('matches', [])
            for match in matches:
                metadata = match.get('metadata', {})
                doc_info = {
                    "title": metadata.get('source', 'Unknown Source'),
                    "content": metadata.get('text', 'No text'),
                    "score": 1.0, # High confidence for explicit citations
                    "type": "article",
                    "article": metadata.get('article'),
                    "url": metadata.get('url'),
                    "references": metadata.get("references", [])
                }
                
                # Add if not already present
                is_present = any(d['content'] == doc_info['content'] for d in articles)
                if not is_present:
                    logging.info(f"   -> Fetched cited Article {doc_info['article']}")
                    articles.append(doc_info)
                    
        except Exception as e:
            logging.error(f"Graph traversal failed: {e}")
            
        return {"chunks": chunks, "articles": articles}

    async def _generate_with_fallback(self, prompt: str):
        # 1. DeepSeek
        try:
            return await self._try_deepseek(prompt)
        except Exception:
            pass
        
        # 2. Gemini
        try:
            return await self._try_gemini(prompt)
        except Exception:
            pass
            
        # 3. Groq
        try:
            return await self._try_groq(prompt)
        except Exception:
            pass
            
        return "⚠️ AI service unavailable."
