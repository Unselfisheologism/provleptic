import pytest
from src.ontology.extractor import OntologyExtractor
from src.ontology.schema import ExtractionResult

def test_ontology_extractor_initialization():
    extractor = OntologyExtractor()
    assert extractor is not None

@pytest.mark.skip(reason="Requires LLM API key")
def test_extraction():
    extractor = OntologyExtractor()
    text = "The Ministry of Rural Development implements PMAY-G in Pune, Maharashtra."
    result = extractor.extract(text, "test_chunk_1")
    assert isinstance(result, ExtractionResult)
    assert len(result.nodes) > 0
    assert len(result.edges) > 0
