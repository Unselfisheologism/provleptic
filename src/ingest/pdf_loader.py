import fitz  # PyMuPDF
import hashlib
from datetime import datetime
from typing import List, Dict
from src.ingest.chunker import TextChunker
from loguru import logger

class PDFLoader:
    def __init__(self, chunker: TextChunker):
        self.chunker = chunker

    def load(self, file_path: str, source_url: str = "local") -> List[Dict]:
        logger.info(f"Loading PDF from {file_path}")
        doc = fitz.open(file_path)
        
        content_hash = hashlib.md5(open(file_path, "rb").read()).hexdigest()
        ingested_at = datetime.now().isoformat()
        
        all_chunks = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            
            metadata = {
                "source": file_path,
                "source_url": source_url,
                "page_number": page_num + 1,
                "ingested_at": ingested_at,
                "content_hash": content_hash,
                "type": "pdf"
            }
            
            chunks = self.chunker.chunk_text(text, metadata)
            all_chunks.extend(chunks)
            
        doc.close()
        return all_chunks
