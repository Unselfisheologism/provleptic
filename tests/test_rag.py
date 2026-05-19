import sys
from unittest.mock import MagicMock

# Mock chromadb and its submodules before importing modules that depend on it
mock_chromadb = MagicMock()
sys.modules["chromadb"] = mock_chromadb
sys.modules["chromadb.config"] = MagicMock()

import pytest
from src.rag.retriever import Retriever
from src.rag.prompt import format_prompt

def test_format_prompt():
    question = "Test question?"
    context_chunks = [
        {
            "content": "Chunk content",
            "metadata": {"source": "test.csv", "row_number": 5}
        }
    ]
    prompt = format_prompt(question, context_chunks)
    assert "Chunk content" in prompt
    assert "test.csv" in prompt
    assert "Row: 5" in prompt

def test_retriever():
    vector_store = MagicMock()
    embedding_service = MagicMock()
    
    embedding_service.embed_query.return_value = [0.1, 0.2]
    vector_store.query.return_value = {
        'documents': [['doc1']],
        'metadatas': [[{'source': 'src1'}]],
        'distances': [[0.5]]
    }
    
    retriever = Retriever(vector_store, embedding_service)
    results = retriever.retrieve("query")
    
    assert len(results) == 1
    assert results[0]['content'] == 'doc1'
    assert results[0]['metadata']['source'] == 'src1'
