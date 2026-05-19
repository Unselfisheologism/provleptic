import spacy
from typing import List, Dict, Any
from .schema import Node, Edge, ExtractionResult
from src.core.opencode_client import opencode_client
import json
from loguru import logger

class OntologyExtractor:
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            logger.warning("spaCy model not found, falling back to basic extraction")
            self.nlp = None

    def extract(self, text: str, source_chunk_id: str) -> ExtractionResult:
        # 1. Use LLM for high-fidelity extraction
        prompt = f"""
        Extract entities and relationships from the following Indian public policy text.
        Entities: Scheme, Ministry, District, State, Outcome, Beneficiary, Target Group.
        Relationships: IMPLEMENTS, TARGETS, LOCATED_IN, ACHIEVED, ADMINISTERS.

        Text:
        {text}

        Return ONLY a JSON object with:
        {{
            "nodes": [{{ "id": "unique_id", "type": "EntityType", "properties": {{ "name": "...", ... }} }}],
            "edges": [{{ "subject_id": "...", "predicate": "RELATION", "object_id": "...", "properties": {{}} }}]
        }}
        """
        
        try:
            response = opencode_client.request_with_retry(
                "chat",
                model="gpt-4", # or whichever model is available
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            data = json.loads(response.choices[0].message.content)
            
            nodes = []
            for n in data.get("nodes", []):
                nodes.append(Node(
                    id=n["id"],
                    type=n["type"],
                    properties=n.get("properties", {}),
                    source_chunk_id=source_chunk_id,
                    confidence=0.9
                ))
            
            edges = []
            for e in data.get("edges", []):
                edges.append(Edge(
                    subject_id=e["subject_id"],
                    predicate=e["predicate"],
                    object_id=e["object_id"],
                    properties=e.get("properties", {}),
                    source_chunk_id=source_chunk_id,
                    confidence=0.8
                ))
                
            if not nodes and self.nlp:
                return self._rule_based_fallback(text, source_chunk_id)

            return ExtractionResult(nodes=nodes, edges=edges)
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            if self.nlp:
                return self._rule_based_fallback(text, source_chunk_id)
            return ExtractionResult(nodes=[], edges=[])

    def _rule_based_fallback(self, text: str, source_chunk_id: str) -> ExtractionResult:
        doc = self.nlp(text)
        nodes = []
        edges = []
        
        # Simple rule: ORG -> Ministry/Scheme, GPE -> State/District
        for ent in doc.ents:
            if ent.label_ == "ORG":
                node_id = self._normalize_id(ent.text, "Entity")
                nodes.append(Node(id=node_id, type="Entity", properties={"name": ent.text}, source_chunk_id=source_chunk_id, confidence=0.5))
            elif ent.label_ == "GPE":
                node_id = self._normalize_id(ent.text, "Location")
                nodes.append(Node(id=node_id, type="Location", properties={"name": ent.text}, source_chunk_id=source_chunk_id, confidence=0.5))
        
        return ExtractionResult(nodes=nodes, edges=edges)

    def _normalize_id(self, text: str, entity_type: str) -> str:
        return f"{entity_type.lower()}:{text.lower().replace(' ', '_')}"
