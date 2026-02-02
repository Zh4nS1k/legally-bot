
import logging
import asyncio
import uuid
import pandas as pd
import json
from io import BytesIO
from legally_bot.services.rag_engine import RAGEngine
from legally_bot.services.resilience import with_retry

class BatchService:
    def __init__(self):
        self.rag = RAGEngine()
        # Semaphore to limit concurrent RAG requests (prevent hitting rate limits)
        self.semaphore = asyncio.Semaphore(5) 

    async def process_file(self, file_content: BytesIO, filename: str) -> BytesIO:
        """
        Processes an Excel or JSON file containing questions.
        Returns an Excel file with answers.
        """
        logging.info(f"📦 Starting batch processing for {filename}")
        
        # 1. Parse File
        try:
            if filename.endswith('.xlsx'):
                df = pd.read_excel(file_content)
            elif filename.endswith('.json'):
                data = json.load(file_content)
                df = pd.DataFrame(data)
            else:
                raise ValueError("Unsupported file format. Use .xlsx or .json")
            
            # Ensure 'question' column exists
            if 'question' not in df.columns:
                 # Try to find a column that looks like a question
                 potential = [c for c in df.columns if 'vopros' in c.lower() or 'quest' in c.lower()]
                 if potential:
                     df.rename(columns={potential[0]: 'question'}, inplace=True)
                 else:
                     raise ValueError("File must contain a 'question' column.")
                     
        except Exception as e:
            logging.error(f"Failed to parse batch file: {e}")
            raise e

        questions = df['question'].tolist()
        results = []
        
        # 2. Process Async
        tasks = [self._process_single_question(q) for q in questions]
        
        # Run with progress tracking
        processed_count = 0
        total = len(tasks)
        
        for task in asyncio.as_completed(tasks):
            result = await task
            results.append(result)
            processed_count += 1
            if processed_count % 5 == 0:
                logging.info(f"   Batch Progress: {processed_count}/{total}")

        # 3. Create Result DataFrame
        # Sort back to original order? asyncio.as_completed yields out of order.
        # Better to wait all
        # Let's re-run with gather to keep order
        results = await asyncio.gather(*tasks) # This keeps order matching 'questions'
        
        result_df = df.copy()
        result_df['ai_answer'] = [r['answer'] for r in results]
        result_df['chunks'] = [str(r['chunks']) for r in results]
        result_df['articles'] = [str(r['articles']) for r in results]
        result_df['status'] = [r.get('status', 'success') for r in results]
        
        # 4. Export
        output = BytesIO()
        result_df.to_excel(output, index=False)
        output.seek(0)
        
        logging.info(f"✅ Batch processing complete for {filename}")
        return output

    @with_retry(attempts=3)
    async def _process_single_question(self, question: str):
        async with self.semaphore:
            try:
                # Use RAG to answer
                response = await self.rag.search(question)
                return {
                    "answer": response['answer'],
                    "chunks": response['chunks'],
                    "articles": response['articles'],
                    "status": "success"
                }
            except Exception as e:
                logging.error(f"Error processing question '{question[:20]}...': {e}")
                return {
                    "answer": "Error",
                    "chunks": [],
                    "articles": [],
                    "status": f"failed: {str(e)}"
                }
