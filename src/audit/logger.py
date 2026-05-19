# src/audit/logger.py
"""Immutable audit logging with SHA-256 hashing for integrity verification."""

import sqlite3
import hashlib
import json
import datetime
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
from loguru import logger


class AuditLogger:
    """
    Immutable audit log writer with SHA-256 hashing.
    
    Implements append-only logging to SQLite. No UPDATE or DELETE operations
    are exposed, ensuring audit trail integrity for compliance purposes.
    
    Features:
    - SHA-256 hashing of queries and results
    - Hash chain linking for tamper detection
    - JSON metadata storage
    - Immutable design (no update/delete methods)
    """

    def __init__(self, db_path: str = "data/audit.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_schema()
        self._last_hash = self._get_last_entry_hash()

    def _init_schema(self):
        """Initialize the audit log table schema."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_role TEXT NOT NULL,
                action TEXT NOT NULL,
                query_hash TEXT NOT NULL,
                result_hash TEXT,
                prev_hash TEXT,
                entry_hash TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        # Create index for faster queries
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
            ON audit_log(timestamp)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_user_role 
            ON audit_log(user_role)
        """)
        self.conn.commit()

    def _get_last_entry_hash(self) -> Optional[str]:
        """Get the hash of the last entry for hash chaining."""
        cursor = self.conn.execute(
            "SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1"
        )
        result = cursor.fetchone()
        return result[0] if result else None

    def _compute_entry_hash(
        self,
        user_role: str,
        action: str,
        query_hash: str,
        result_hash: Optional[str],
        timestamp: str,
        prev_hash: Optional[str],
        metadata: Optional[str]
    ) -> str:
        """Compute SHA-256 hash of the entire entry for integrity."""
        entry_data = (
            f"{user_role}|{action}|{query_hash}|{result_hash}|{timestamp}|{prev_hash}|{metadata}"
        )
        return hashlib.sha256(entry_data.encode()).hexdigest()

    def log(
        self,
        role: str,
        action: str,
        query: str,
        result: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> int:
        """
        Log an audit entry.
        
        Args:
            role: User role (analyst, field_officer, policymaker)
            action: Action performed (query, rule_evaluation, export, etc.)
            query: The query or input that triggered this action
            result: The result/output of the action
            metadata: Additional context (rule_id, district, etc.)
            user_id: Optional user identifier
            session_id: Optional session identifier
        
        Returns:
            The ID of the inserted entry
        """
        timestamp = datetime.datetime.utcnow().isoformat()
        
        # Compute hashes
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        result_hash = hashlib.sha256(
            json.dumps(result, sort_keys=True).encode()
        ).hexdigest() if result else None
        
        # Chain to previous entry
        prev_hash = self._last_hash
        
        # Compute entry hash for integrity
        metadata_str = json.dumps(metadata, sort_keys=True) if metadata else None
        entry_hash = self._compute_entry_hash(
            role, action, query_hash, result_hash, timestamp, prev_hash, metadata_str
        )
        
        # Build extended metadata
        extended_metadata = metadata or {}
        if user_id:
            extended_metadata["user_id"] = user_id
        if session_id:
            extended_metadata["session_id"] = session_id
        
        cursor = self.conn.execute(
            """
            INSERT INTO audit_log 
            (user_role, action, query_hash, result_hash, prev_hash, entry_hash, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                role,
                action,
                query_hash,
                result_hash,
                prev_hash,
                entry_hash,
                timestamp,
                json.dumps(extended_metadata) if extended_metadata else None
            )
        )
        self.conn.commit()
        
        # Update chain pointer
        self._last_hash = entry_hash
        
        logger.info(f"Audit log entry created: {action} by {role}")
        return cursor.lastrowid

    def get_entries(
        self,
        limit: int = 100,
        offset: int = 0,
        role_filter: Optional[str] = None,
        action_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve audit log entries with optional filtering."""
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        
        if role_filter:
            query += " AND user_role = ?"
            params.append(role_filter)
        
        if action_filter:
            query += " AND action = ?"
            params.append(action_filter)
        
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = self.conn.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        
        entries = []
        for row in cursor.fetchall():
            entry = dict(zip(columns, row))
            # Parse metadata JSON
            if entry.get("metadata"):
                try:
                    entry["metadata_parsed"] = json.loads(entry["metadata"])
                except:
                    pass
            entries.append(entry)
        
        return entries

    def get_entry_by_id(self, entry_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific audit entry by ID."""
        cursor = self.conn.execute(
            "SELECT * FROM audit_log WHERE id = ?",
            (entry_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        columns = [desc[0] for desc in cursor.description]
        entry = dict(zip(columns, row))
        if entry.get("metadata"):
            try:
                entry["metadata_parsed"] = json.loads(entry["metadata"])
            except:
                pass
        return entry

    def verify_chain_integrity(self) -> Dict[str, Any]:
        """
        Verify the integrity of the hash chain.
        
        Returns:
            Dict with verification results: {
                "valid": bool,
                "entries_checked": int,
                "first_invalid_id": Optional[int],
                "message": str
            }
        """
        cursor = self.conn.execute(
            "SELECT * FROM audit_log ORDER BY id ASC"
        )
        columns = [desc[0] for desc in cursor.description]
        
        entries_checked = 0
        prev_hash = None
        first_invalid = None
        
        for row in cursor.fetchall():
            entry = dict(zip(columns, row))
            entry_id = entry["id"]
            entry_prev_hash = entry["prev_hash"]
            entry_hash = entry["entry_hash"]
            
            # Check chain link
            if prev_hash is not None and entry_prev_hash != prev_hash:
                first_invalid = entry_id
                break
            
            # Verify entry hash
            expected_hash = self._compute_entry_hash(
                entry["user_role"],
                entry["action"],
                entry["query_hash"],
                entry["result_hash"],
                entry["timestamp"],
                entry["prev_hash"],
                entry["metadata"]
            )
            
            if entry_hash != expected_hash:
                first_invalid = entry_id
                break
            
            prev_hash = entry_hash
            entries_checked += 1
        
        if first_invalid is None and entries_checked > 0:
            return {
                "valid": True,
                "entries_checked": entries_checked,
                "first_invalid_id": None,
                "message": f"All {entries_checked} entries verified successfully"
            }
        elif entries_checked == 0:
            return {
                "valid": True,
                "entries_checked": 0,
                "first_invalid_id": None,
                "message": "No entries to verify"
            }
        else:
            return {
                "valid": False,
                "entries_checked": entries_checked,
                "first_invalid_id": first_invalid,
                "message": f"Chain broken at entry {first_invalid}"
            }

    def count_entries(self) -> int:
        """Get total count of audit entries."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM audit_log")
        return cursor.fetchone()[0]

    def close(self):
        """Close the database connection."""
        self.conn.close()

    def __del__(self):
        """Ensure connection is closed."""
        try:
            self.conn.close()
        except:
            pass


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger