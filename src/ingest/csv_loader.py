import pandas as pd
import hashlib
from datetime import datetime
from typing import List, Dict
from src.ingest.chunker import TextChunker
from loguru import logger

class CSVLoader:
    def __init__(self, chunker: TextChunker):
        self.chunker = chunker

    def load(self, file_path: str, source_url: str = "local") -> List[Dict]:
        logger.info(f"Loading CSV from {file_path}")
        df = pd.read_csv(file_path)
        
        # Normalize column names to snake_case
        df.columns = [col.lower().replace(" ", "_") for col in df.columns]
        
        content_hash = hashlib.md5(df.to_csv().encode()).hexdigest()
        ingested_at = datetime.now().isoformat()
        
        all_chunks = []
        for index, row in df.iterrows():
            # Convert row to a text representation for embedding
            content = " | ".join([f"{col}: {val}" for col, val in row.items()])
            metadata = {
                "source": file_path,
                "source_url": source_url,
                "row_number": index,
                "ingested_at": ingested_at,
                "content_hash": content_hash,
                "type": "csv"
            }
            # For CSV, we might not need further chunking if rows are small, 
            # but let's pass it through the chunker just in case or to keep it consistent.
            chunks = self.chunker.chunk_text(content, metadata)
            all_chunks.extend(chunks)
            
        return all_chunks
