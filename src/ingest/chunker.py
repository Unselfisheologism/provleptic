from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict

class TextChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

    def chunk_text(self, text: str, metadata: Dict) -> List[Dict]:
        chunks = self.splitter.split_text(text)
        chunked_data = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_index"] = i
            chunked_data.append({
                "content": chunk,
                "metadata": chunk_metadata
            })
        return chunked_data
