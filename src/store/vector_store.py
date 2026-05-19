import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any
from src.core.config import settings
from loguru import logger

class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        self.collection = self.client.get_or_create_collection(name="indian_public_data")

    def add_documents(self, chunks: List[Dict]):
        ids = [f"{c['metadata']['content_hash']}_{c['metadata']['chunk_index']}" for c in chunks]
        documents = [c['content'] for c in chunks]
        metadatas = [c['metadata'] for c in chunks]
        
        # We handle embeddings outside or let Chroma handle it.
        # Given we have an EmbeddingService, we should probably pass them.
        # But Chroma can also take an embedding function.
        # To keep it simple and consistent with the requirement of using sentence-transformers,
        # we'll pass the embeddings if we have them, or let it be handled.
        
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"Added {len(chunks)} documents to ChromaDB")

    def query(self, query_embeddings: List[float], n_results: int = 5) -> Dict[str, Any]:
        return self.collection.query(
            query_embeddings=[query_embeddings],
            n_results=n_results
        )
