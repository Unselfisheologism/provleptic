import pytest
from src.ontology.lineage import LineageTracker
from src.store.metadata_store import MetadataStore

def test_lineage_tracker():
    # Mock metadata store if needed, but for now we test the tracker
    metadata_store = MetadataStore(":memory:")
    tracker = LineageTracker(metadata_store)
    details = tracker.get_source_details("test_chunk_id")
    assert "chunk_id" in details
    assert details["chunk_id"] == "test_chunk_id"
