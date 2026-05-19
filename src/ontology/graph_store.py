import networkx as nx
import sqlite3
import json
import os
from typing import List, Optional, Dict, Any
from .schema import Node, Edge
from datetime import datetime

class GraphStore:
    def __init__(self, db_path: str = "data/ontology.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.G = nx.DiGraph()
        self._init_db()
        self._load_from_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    properties_json TEXT,
                    source_chunk_id TEXT,
                    confidence REAL,
                    created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id TEXT,
                    predicate TEXT,
                    object_id TEXT,
                    properties_json TEXT,
                    source_chunk_id TEXT,
                    confidence REAL,
                    created_at TEXT,
                    FOREIGN KEY(subject_id) REFERENCES nodes(id),
                    FOREIGN KEY(object_id) REFERENCES nodes(id)
                )
            """)

    def _load_from_db(self):
        with sqlite3.connect(self.db_path) as conn:
            nodes = conn.execute("SELECT * FROM nodes").fetchall()
            for n in nodes:
                self.G.add_node(n[0], type=n[1], **json.loads(n[2]), source_chunk_id=n[3], confidence=n[4])
            
            edges = conn.execute("SELECT * FROM edges").fetchall()
            for e in edges:
                self.G.add_edge(e[1], e[3], predicate=e[2], **json.loads(e[4]), source_chunk_id=e[5], confidence=e[6])

    def add_node(self, node: Node):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO nodes (id, type, properties_json, source_chunk_id, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (node.id, node.type, json.dumps(node.properties), node.source_chunk_id, node.confidence, node.created_at.isoformat()))
        self.G.add_node(node.id, type=node.type, **node.properties, source_chunk_id=node.source_chunk_id, confidence=node.confidence)

    def add_edge(self, edge: Edge):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO edges (subject_id, predicate, object_id, properties_json, source_chunk_id, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (edge.subject_id, edge.predicate, edge.object_id, json.dumps(edge.properties), edge.source_chunk_id, edge.confidence, edge.created_at.isoformat()))
        self.G.add_edge(edge.subject_id, edge.object_id, predicate=edge.predicate, **edge.properties, source_chunk_id=edge.source_chunk_id, confidence=edge.confidence)

    def get_graph(self) -> nx.DiGraph:
        return self.G

    def search_nodes(self, query: str, node_type: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for n, data in self.G.nodes(data=True):
            if node_type and data.get('type') != node_type:
                continue
            if query.lower() in n.lower() or any(query.lower() in str(v).lower() for v in data.values()):
                results.append({"id": n, **data})
        return results
