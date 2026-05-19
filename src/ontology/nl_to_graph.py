import networkx as nx
from typing import List, Dict, Any
from src.core.opencode_client import opencode_client
import json
from loguru import logger

class GraphQueryTranslator:
    def __init__(self, G: nx.DiGraph):
        self.G = G

    def query(self, nl_query: str) -> List[Dict[str, Any]]:
        # For complex queries, use LLM to translate to a search/traversal plan
        # For this phase, we'll use LLM to identify intent and entities
        
        prompt = f"""
        Given the following property graph schema and a natural language query, return a list of nodes and edges that satisfy the query.
        
        Schema:
        Nodes: Scheme, Ministry, District, State, Outcome, Beneficiary, Target Group
        Edges: IMPLEMENTS, TARGETS, LOCATED_IN, ACHIEVED, ADMINISTERS
        
        Available Nodes (Sample):
        {list(self.G.nodes(data=True))[:10]}
        
        Query: {nl_query}
        
        Return ONLY a JSON list of matching node IDs or a traversal result.
        {{
            "results": [{{ "id": "...", "type": "...", "properties": {{}} }}]
        }}
        """
        
        try:
            response = opencode_client.request_with_retry(
                "chat",
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            data = json.loads(response.choices[0].message.content)
            result_ids = [r["id"] for r in data.get("results", [])]
            
            final_results = []
            for nid in result_ids:
                if nid in self.G:
                    final_results.append({"id": nid, **self.G.nodes[nid]})
            
            return final_results
        except Exception as e:
            logger.error(f"NL to Graph query failed: {e}")
            # Fallback: simple keyword search
            results = []
            for n, data in self.G.nodes(data=True):
                if any(word.lower() in str(v).lower() for word in nl_query.split() for v in data.values()):
                    results.append({"id": n, **data})
            return results[:5]
