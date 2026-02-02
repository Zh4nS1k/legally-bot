import os
import logging
import uuid
import re
from io import BytesIO
import trafilatura
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from legally_bot.config import settings

class IngestionService:
    def __init__(self):
        try:
            self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            self.index = self.pc.Index(settings.PINECONE_INDEX_NAME)
            self.encoder = SentenceTransformer('BAAI/bge-large-en-v1.5')
            logging.info("✅ Ingestion Service initialized (RAG 2.0)")
        except Exception as e:
            logging.error(f"❌ Failed to init Ingestion Service: {e}")
            self.index = None

    async def ingest_file(self, file_content: BytesIO, file_name: str, file_type: str):
        """
        Ingests a file with semantic chunking.
        Treats file content as a single 'Article' or attempts to split if structure is found.
        (For files, metadata is limited to filename).
        """
        logging.info(f"📥 Ingesting file: {file_name} ({file_type})")
        
        text = ""
        try:
            if file_type == "pdf":
                from pypdf import PdfReader
                reader = PdfReader(file_content)
                text = "\n\n".join([page.extract_text() or "" for page in reader.pages])
            elif file_type == "docx":
                import docx
                doc = docx.Document(file_content)
                text = "\n".join([para.text for para in doc.paragraphs])
            elif file_type == "md" or file_type == "txt":
                text = file_content.getvalue().decode("utf-8")
        except Exception as e:
            logging.error(f"Failed to extract text from {file_name}: {e}")
            return 0
            
        if not text or len(text) < 100:
            logging.warning(f"File {file_name} content too short to index.")
            return 0

        # Files usually don't have perfect Article structure like strict laws, 
        # so we default to a simpler chunking or try to apply the same logic if it looks like a law.
        chunks_data = self._semantic_chunking(text, source_title=file_name, source_url="Uploaded File")
        await self._upload_to_pinecone(chunks_data)
        return len(chunks_data)

    async def ingest_url(self, url: str):
        """
        Scrapes URL using Trafilatura (via custom request), cleans noise, extracts metadata, 
        chunks by 'Article', and uploads.
        """
        logging.info(f"🌐 Ingesting URL (RAG 2.0): {url}")
        
        # Use requests directly to handle SSL and headers better than trafilatura.fetch_url
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        try:
            # First try with verification, fallback to False if needed, but for zan.kz usually False is safer strictly for scraping
            # We'll just set verify=False directly as this is a known issue for the user.
            response = requests.get(url, headers=headers, verify=False, timeout=30)
            response.raise_for_status()
            response.encoding = response.apparent_encoding # Ensure correct encoding (utf-8/cp1251 etc)
            downloaded = response.text
        except Exception as e:
            logging.error(f"Failed to fetch URL {url}: {e}")
            return 0
            
        # Extract text and metadata
        text = trafilatura.extract(downloaded, include_comments=False, include_tables=False, no_fallback=True)
        if not text or len(text) < 200:
            logging.warning(f"Extracted text too short for {url}")
            return 0

        # Extract Title (Metadata)
        # We can extract metadata from the downloaded HTML string
        metadata = trafilatura.extract_metadata(downloaded)
        law_title = metadata.title if metadata and metadata.title else "Unknown Law"
        
        logging.info(f"   Document Title: {law_title}")

        # Clean text (Custom Regex for Adilet/Zan)
        text = self._clean_text(text)
        
        # Semantic Chunking
        chunks_data = self._semantic_chunking(text, source_title=law_title, source_url=url)
        
        if not chunks_data:
            logging.warning("No valid chunks created.")
            return 0
            
        await self._upload_to_pinecone(chunks_data)
        return len(chunks_data)

    def _clean_text(self, text: str) -> str:
        """
        Removes UI noise specific to adilet.zan.kz and general web garbage.
        """
        patterns = [
            r"Enter search query",
            r"Return to mobile version",
            r"Republican State Enterprise",
            r"© All rights reserved",
            r"Вернуться в мобильную версию",
            r"Введите поисковый запрос",
            r"Республиканское государственное предприятие",
            r"© Все права защищены",
            r"^\s*Search\s*$",
            r"^\s*Меню\s*$",
        ]
        
        cleaned_lines = []
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            is_noise = False
            for p in patterns:
                if re.search(p, line, re.IGNORECASE):
                    is_noise = True
                    break
            
            if not is_noise:
                cleaned_lines.append(line)
                
        return "\n".join(cleaned_lines)

    def _semantic_chunking(self, text: str, source_title: str, source_url: str):
        """
        Splits text into chunks based on 'Article X' / 'Статья X'.
        Returns a list of dicts: {'text': ..., 'article': ..., 'source': ..., 'url': ...}
        """
        # 1. Split by Article Header
        # Regex captures the header "Article 1" or "Статья 1" (Dot is optional/missing in trafilatura output)
        pattern = r"((?:Article|Статья)\s+\d+)"
        parts = re.split(pattern, text)
        
        chunks = []
        
        # parts[0] is text before first article (Preamble)
        if parts[0].strip():
            chunks.append({
                "text": parts[0].strip(),
                "article": "Preamble",
                "source": source_title,
                "url": source_url,
                "type": "chunk"
            })
            
        # Iterate over the rest: odd indices are headers, even are content
        for i in range(1, len(parts), 2):
            header = parts[i].strip() # e.g. "Статья 1"
            content = parts[i+1].strip() if i+1 < len(parts) else ""
            
            # Extract number from header
            num_match = re.search(r"\d+", header)
            article_num = num_match.group(0) if num_match else "Unknown"
            
            full_text = f"{header}\n{content}"
            
            # Integrity Rule: Length check
            if len(full_text) < 50:
                continue # Skip tiny fragments
                
            chunks.append({
                "text": full_text,
                "article": article_num,
                "source": source_title,
                "url": source_url,
                "type": "article"
            })
                
        return chunks

    def _split_large_chunk(self, text: str, max_size=2000, overlap=100):
        """
        Simple overlapping splitter for large articles.
        """
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(chunk_size=max_size, chunk_overlap=overlap)
        return splitter.split_text(text)

    async def _upload_to_pinecone(self, chunks_data: list):
        if not self.index:
            logging.error("Pinecone index not available.")
            return

        logging.info(f"⬆️ Uploading {len(chunks_data)} semantic chunks to Pinecone...")
        
        # FINAL SAFETY CHECK: Split any chunk > 35KB (approx 15-20k chars depending on encoding)
        # Pinecone limit is 40KB for metadata.
        # Safe limit: 10,000 characters (UTF-8 ~10-40KB, usually 1 byte/char for English, 2 for Russian)
        SAFE_CHAR_LIMIT = 8000 
        
        final_chunks = []
        for chunk in chunks_data:
            if len(chunk['text'].encode('utf-8')) > 35000: # Check bytes roughly
                 # Split massive chunk
                 logging.warning(f"Chunk Article {chunk['article']} is too large. Splitting...")
                 sub_texts = self._split_large_chunk(chunk['text'], max_size=SAFE_CHAR_LIMIT)
                 for idx, sub_text in enumerate(sub_texts):
                     new_chunk = chunk.copy()
                     new_chunk['text'] = sub_text
                     new_chunk['article'] = f"{chunk['article']} (Part {idx+1})"
                     final_chunks.append(new_chunk)
            else:
                final_chunks.append(chunk)

        chunks_data = final_chunks
        
        # Encode all at once for speed
        texts = [c['text'] for c in chunks_data]
        embeddings = self.encoder.encode(texts)
        
        vectors = []
        for i, chunk_data in enumerate(chunks_data):
            vector_id = str(uuid.uuid4())
            embedding = embeddings[i].tolist()
            
            metadata = {
                "text": chunk_data['text'],
                "source": chunk_data['source'],
                "url": chunk_data['url'],
                "article": str(chunk_data['article']),
                "type": chunk_data['type']
            }
            vectors.append((vector_id, embedding, metadata))
        
        batch_size = 50 # Reduced batch size for safety
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            try:
                self.index.upsert(vectors=batch)
                logging.info(f"   Upserted batch {i//batch_size + 1}")
            except Exception as e:
                logging.error(f"   ❌ Batch upload failed: {e}")

