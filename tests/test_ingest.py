import pytest
import os
import pandas as pd
from src.ingest.chunker import TextChunker
from src.ingest.csv_loader import CSVLoader

def test_chunker():
    chunker = TextChunker(chunk_size=10, chunk_overlap=2)
    text = "This is a long text for testing chunking."
    chunks = chunker.chunk_text(text, {"meta": "data"})
    assert len(chunks) > 1
    assert chunks[0]["metadata"]["meta"] == "data"
    assert "chunk_index" in chunks[0]["metadata"]

def test_csv_loader(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    csv_file = d / "test.csv"
    df = pd.DataFrame({
        "District Name": ["Pune", "Mumbai"],
        "Value": [10, 20]
    })
    df.to_csv(csv_file, index=False)
    
    chunker = TextChunker()
    loader = CSVLoader(chunker)
    chunks = loader.load(str(csv_file))
    
    assert len(chunks) == 2
    assert "district_name" in chunks[0]["content"].lower()
    assert chunks[0]["metadata"]["row_number"] == 0
