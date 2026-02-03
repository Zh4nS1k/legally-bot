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
            # RAG 4.0: Cross-Encoder for Re-ranking
            from sentence_transformers import CrossEncoder
            self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            
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
            
            # RAG 4.0: Retrieve & Re-rank
            # 1. Retrieve more candidates (Top-20)
            initial_k = 20
            results = self.index.query(vector=vector, top_k=initial_k, include_metadata=True)
            
            matches = results.get('matches', [])
            
            # 2. Re-rank with Cross-Encoder
            if matches and self.cross_encoder:
                # Prepare pairs: (Query, Document Text)
                pairs = [[query, m['metadata'].get('text', '')] for m in matches]
                scores = self.cross_encoder.predict(pairs)
                
                # Attach new scores
                for match, score in zip(matches, scores):
                    match['score'] = float(score) # Update score
                    
                # Sort by new score descending
                matches.sort(key=lambda x: x['score'], reverse=True)
                
                # Log re-ranking effect
                logging.info(f"Re-ranked top result: {matches[0]['metadata'].get('title')} (Score: {matches[0]['score']:.4f})")
            
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

            # Determine language instruction
            lang_instruction = "Respond in Russian."
            if lang == "en":
                lang_instruction = "Respond in English."
            elif lang == "kk":
                lang_instruction = "Respond in Kazakh. Use formal Kazakh legal terminology."

            logging.info(f"Target Language: {lang}")

            # 0. Chit-chat check
            # We do a quick check if the query is just "Hello", "How are you", etc.
            # To save tokens, we can use a small heuristic or just ask LLM with a tiny prompt.
            # But robust way is:
            if self._is_general_chat(query):
                logging.info("💬 General chat detected. Bypassing RAG.")
                simple_prompt = f"User says: {query}\n\nReply helpfully and politely. {lang_instruction} If they ask for legal advice, mention you can help with Kazakhstan law."
                simple_answer = await self._generate_with_fallback(simple_prompt)
                return {
                    "answer": simple_answer,
                    "chunks": [],
                    "articles": []
                }

            # 1. Extraction (Retrieval)
            # Already done above (Vector Search + Re-ranking + Expansion)
            # chunks and articles are ready.

            context_text = ""
            for d in chunks + articles:
                context_text += f"---\nSource: {d.get('title', 'Unknown')}\n"
                context_text += f"Article: {d.get('article', 'N/A')}\n"
                context_text += f"URL: {d.get('url', 'N/A')}\n"
                context_text += f"Content: {d['content']}\n"
            
            # 2. Generation 1 (Draft / Reasoning)
            draft_prompt = f"""
            Role: Expert Legal Analyst for Kazakhstan Law.
            Task: Analyze the context and draft a comprehensive answer to the question.
            
            Context:
            {context_text}
            
            Question: {query}
            
            Instructions:
            - Think step-by-step.
            - Identify relevant articles from context.
            - specific legal norms.
            - {lang_instruction}
            
            Draft Answer:
            """
            draft_answer = await self._generate_with_fallback(draft_prompt)
            
            # 3. Generation 2 (Refinement / Critique)
            refine_prompt = f"""
            Role: Senior Chief Editor.
            Task: Critique and refine the Draft Answer.
            
            Context:
            {context_text}
            
            Draft Answer:
            {draft_answer}
            
            User Question: {query}
            
            Instructions:
            - Verify accuracy against Context.
            - Remove hallucinations.
            - Improve clarity and flow.
            - Ensure tone is professional and empathetic.
            - {lang_instruction}
            
            Refined Answer:
            """
            refined_answer = await self._generate_with_fallback(refine_prompt)

            # 4. Extraction (Final Formatting / Citations)
            # Extract key references into a structured list to ensure user sees them clearly
            extract_prompt = f"""
            Task: Extract metadata and formatting from the Refined Answer.
            
            Refined Answer:
            {refined_answer}
            
            Instructions:
            - Return the Refined Answer exactly as is, but ensure that at the bottom, there is a clear list of "Used Sources" if applicable.
            - If sources are already listed, just return the text.
            - {lang_instruction}
            
            Final Output:
            """
            final_answer = await self._generate_with_fallback(extract_prompt)
            
            return {
                "answer": final_answer,
                "chunks": chunks[:num_chunks],
                "articles": articles[:num_articles]
            }

        except Exception as e:
            logging.error(f"Search overall failed: {e}", exc_info=True)
            return {"answer": "Error during search.", "chunks": [], "articles": []}

    def _is_general_chat(self, query: str) -> bool:
        """
        Simple heuristic to detect non-legal, general chit-chat.
        """
        greetings = [
            "hello", "hi", "hey", "start", "привет", "здравствуйте", "салем", "сәлем", 
            "how are you", "как дела", "who are you", "кто ты", "ты кто"
        ]
        
        # Check for short, common greetings
        q_lower = query.lower().strip().replace("?", "").replace("!", "")
        if q_lower in greetings:
            return True
        
        # Check length - very short queries are rarely complex legal questions
        if len(query.split()) < 2 and q_lower not in ["law", "закон", "заң"]:
            return True
            
        return False

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
