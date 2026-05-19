import pytest
import networkx as nx
from src.ontology.nl_to_graph import GraphQueryTranslator

def test_graph_query_translator_fallback():
    G = nx.DiGraph()
    G.add_node("scheme:pmay", type="Scheme", name="PMAY")
    translator = GraphQueryTranslator(G)
    
    # Test fallback search
    results = translator.query("PMAY")
    assert len(results) > 0
    assert results[0]["id"] == "scheme:pmay"
