from sentence_transformers import SentenceTransformer
from typing import List
from src.core.config import settings

class EmbeddingService:
    def __init__(self, model_name: str = None):
        if model_name is None:
            model_name = settings.EMBEDDING_MODEL
        self.model = SentenceTransformer(model_name)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        return self.model.encode([text])[0].tolist()
