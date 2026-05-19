from typing import List, Dict, Any
from src.store.vector_store import VectorStore
from src.embed.embedding_service import EmbeddingService
from loguru import logger

class Retriever:
    def __init__(self, vector_store: VectorStore, embedding_service: EmbeddingService):
        self.vector_store = vector_store
        self.embedding_service = embedding_service

    def retrieve(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        logger.info(f"Retrieving context for query: {query}")
        query_embedding = self.embedding_service.embed_query(query)
        results = self.vector_store.query(query_embedding, n_results=n_results)
        
        chunks = []
        # ChromaDB results format is results['documents'][0], results['metadatas'][0], etc.
        if results['documents']:
            for i in range(len(results['documents'][0])):
                chunks.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })
        
        return chunks
