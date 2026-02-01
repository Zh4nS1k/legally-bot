import os
import logging
import uuid
from io import BytesIO
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from legally_bot.config import settings

class IngestionService:
    def __init__(self):
        try:
            self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            self.index = self.pc.Index(settings.PINECONE_INDEX_NAME)
            self.encoder = SentenceTransformer('BAAI/bge-large-en-v1.5')
            logging.info("✅ Ingestion Service initialized")
        except Exception as e:
            logging.error(f"❌ Failed to init Ingestion Service: {e}")
            self.index = None

    async def ingest_file(self, file_content: BytesIO, file_name: str, file_type: str):
        """
        Reads file content from BytesIO, chunks text, embeds, and uploads to Pinecone.
        Uses a retry mechanism with different extraction strategies.
        """
        logging.info(f"📥 Ingesting file: {file_name} ({file_type})")
        
        text = ""
        max_attempts = 3
        
        for attempt in range(1, max_attempts + 1):
            logging.info(f"   Attempt {attempt}/3 for {file_name}")
            try:
                if file_type == "pdf":
                    text = await self._extract_pdf_with_strategy(file_content, attempt)
                elif file_type == "docx":
                    text = self._extract_docx(file_content)
                elif file_type == "md":
                    text = file_content.getvalue().decode("utf-8")
                
                if text and text.strip():
                    logging.info(f"   ✅ Successfully extracted {len(text)} characters on attempt {attempt}")
                    break
                else:
                    logging.warning(f"   ⚠️ Attempt {attempt} returned empty text for {file_name}")
            except Exception as e:
                logging.error(f"   ❌ Attempt {attempt} failed for {file_name}: {e}")
            
            # Reset buffer for next attempt
            file_content.seek(0)
            
        if not text or not text.strip():
            logging.error(f"Final failure: No text extracted from {file_name} after {max_attempts} attempts.")
            return 0

        chunks = self._chunk_text(text)
        await self._upload_to_pinecone(chunks, source=file_name)
        return len(chunks)

    async def _extract_pdf_with_strategy(self, file_content: BytesIO, strategy: int):
        """
        Strategy 1: pypdf (Fast, standard)
        Strategy 2: pdfplumber (Better for complex layouts)
        Strategy 3: pypdf with layout mode (if available) or raw stream
        """
        if strategy == 1:
            from pypdf import PdfReader
            reader = PdfReader(file_content)
            return "\n\n".join([page.extract_text() or "" for page in reader.pages])
        
        elif strategy == 2:
            import pdfplumber
            with pdfplumber.open(file_content) as pdf:
                return "\n\n".join([page.extract_text() or "" for page in pdf.pages])
        
        elif strategy == 3:
            # Try pypdf with specialized extraction or just a more aggressive clean
            from pypdf import PdfReader
            reader = PdfReader(file_content)
            text = ""
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
            return text
        return ""

    def _extract_docx(self, file_content: BytesIO):
        import docx
        doc = docx.Document(file_content)
        return "\n".join([para.text for para in doc.paragraphs])

    async def ingest_url(self, url: str):
        """
        Scrapes URL, chunks, embeds, uploads.
        Uses a retry mechanism with different scraping parameters.
        """
        logging.info(f"🌐 Ingesting URL: {url}")
        text = ""
        max_attempts = 3
        
        import requests
        from bs4 import BeautifulSoup
        import urllib3
        # Disable insecure request warnings for verify=False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        for attempt in range(1, max_attempts + 1):
            logging.info(f"   Attempt {attempt}/3 for {url}")
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                
                # Varying strategies per attempt
                verify_ssl = True if attempt == 3 else False # Try without verify first, then with (just in case)
                timeout = 10 * attempt
                
                if attempt == 2:
                    # Strategy 2: Different User-Agent and referer
                    headers['User-Agent'] = 'Googlebot/2.1 (+http://www.google.com/bot.html)'
                    headers['Referer'] = 'https://www.google.com/'

                resp = requests.get(url, headers=headers, verify=verify_ssl, timeout=timeout)
                resp.raise_for_status()
                
                # Detect encoding
                resp.encoding = resp.apparent_encoding
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                
                text = soup.get_text(separator=' ', strip=True)
                
                if text and len(text) > 100: # Basic quality check
                    logging.info(f"   ✅ Successfully scraped {len(text)} characters on attempt {attempt}")
                    break
                else:
                    logging.warning(f"   ⚠️ Attempt {attempt} returned too little text ({len(text) if text else 0} chars)")
            except Exception as e:
                logging.error(f"   ❌ Attempt {attempt} failed for {url}: {e}")
        
        if not text or not text.strip():
            logging.error(f"Final failure: No text extracted from URL {url} after {max_attempts} attempts.")
            return 0
            
        chunks = self._chunk_text(text)
        await self._upload_to_pinecone(chunks, source=url)
        return len(chunks)

    def _chunk_text(self, text: str):
        return self.text_splitter.split_text(text)

    async def _upload_to_pinecone(self, chunks: list, source: str):
        if not self.index:
            logging.error("Pinecone index not available.")
            return

        logging.info(f"⬆️ Uploading {len(chunks)} chunks to Pinecone...")
        
        # Batch upload could be optimized, but doing simple loop/batch here
        vectors = []
        
        # Encode all at once for speed
        embeddings = self.encoder.encode(chunks)
        
        for i, chunk in enumerate(chunks):
            vector_id = str(uuid.uuid4())
            embedding = embeddings[i].tolist()
            metadata = {
                "text": chunk,
                "source": source,
                "chunk_index": i
            }
            vectors.append((vector_id, embedding, metadata))
        
        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            self.index.upsert(vectors=batch)
            logging.info(f"   Upserted batch {i//batch_size + 1}")
