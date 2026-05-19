import sqlite3
import os
from src.core.config import settings

class MetadataStore:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(settings.CHROMA_PERSIST_DIR, "metadata.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT,
                source_url TEXT,
                ingested_at TEXT,
                content_hash TEXT UNIQUE
            )
        """)
        self.conn.commit()

    def log_ingestion(self, file_name: str, source_url: str, ingested_at: str, content_hash: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO ingestion_log (file_name, source_url, ingested_at, content_hash)
            VALUES (?, ?, ?, ?)
        """, (file_name, source_url, ingested_at, content_hash))
        self.conn.commit()

    def get_all_ingestions(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ingestion_log")
        return cursor.fetchall()
