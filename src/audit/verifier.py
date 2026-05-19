# src/audit/verifier.py
"""Audit log verification utilities for integrity checking."""

import hashlib
import json
from typing import Dict, List, Optional, Any, Tuple
from loguru import logger


class AuditVerifier:
    """
    Verifies the integrity of audit log entries and hash chains.
    
    Can verify individual entries or the entire chain.
    """

    def __init__(self, audit_logger):
        """
        Initialize verifier with an audit logger instance.
        
        Args:
            audit_logger: An AuditLogger instance to verify
        """
        self.audit_logger = audit_logger

    def verify_entry(self, entry_id: int) -> Dict[str, Any]:
        """
        Verify a single audit entry's integrity.
        
        Args:
            entry_id: The ID of the entry to verify
        
        Returns:
            Dict with verification results
        """
        entry = self.audit_logger.get_entry_by_id(entry_id)
        if not entry:
            return {
                "valid": False,
                "entry_id": entry_id,
                "message": "Entry not found"
            }
        
        return self._verify_entry_data(entry)

    def _verify_entry_data(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Verify the integrity of entry data."""
        expected_hash = self._compute_entry_hash(entry)
        actual_hash = entry.get("entry_hash")
        
        if expected_hash != actual_hash:
            return {
                "valid": False,
                "entry_id": entry.get("id"),
                "query_hash": entry.get("query_hash"),
                "message": "Entry hash mismatch - possible tampering detected",
                "expected_hash": expected_hash,
                "actual_hash": actual_hash
            }
        
        return {
            "valid": True,
            "entry_id": entry.get("id"),
            "query_hash": entry.get("query_hash"),
            "message": "Entry verified successfully",
            "timestamp": entry.get("timestamp"),
            "action": entry.get("action"),
            "user_role": entry.get("user_role")
        }

    def _compute_entry_hash(self, entry: Dict[str, Any]) -> str:
        """Recompute the expected entry hash."""
        metadata = entry.get("metadata")
        metadata_str = json.dumps(json.loads(metadata), sort_keys=True) if metadata else None
        
        entry_data = (
            f"{entry['user_role']}|{entry['action']}|{entry['query_hash']}|"
            f"{entry['result_hash']}|{entry['timestamp']}|{entry['prev_hash']}|{metadata_str}"
        )
        return hashlib.sha256(entry_data.encode()).hexdigest()

    def verify_chain(self) -> Dict[str, Any]:
        """
        Verify the entire hash chain.
        
        Returns:
            Complete chain verification results
        """
        return self.audit_logger.verify_chain_integrity()

    def verify_query_hash(self, entry_id: int, original_query: str) -> Dict[str, Any]:
        """
        Verify that a query matches its logged hash.
        
        Args:
            entry_id: The audit entry ID
            original_query: The original query string to verify
        
        Returns:
            Verification result with match status
        """
        entry = self.audit_logger.get_entry_by_id(entry_id)
        if not entry:
            return {"valid": False, "message": "Entry not found"}
        
        computed_hash = hashlib.sha256(original_query.encode()).hexdigest()
        logged_hash = entry.get("query_hash")
        
        return {
            "valid": computed_hash == logged_hash,
            "computed_hash": computed_hash,
            "logged_hash": logged_hash,
            "match": computed_hash == logged_hash
        }

    def get_entry_lineage(self, entry_id: int) -> List[Dict[str, Any]]:
        """
        Trace the lineage of an entry back through the hash chain.
        
        Args:
            entry_id: Starting entry ID
        
        Returns:
            List of entries in the chain from beginning to the specified entry
        """
        lineage = []
        current_id = entry_id
        
        # Walk backwards to find the start
        entries = self.audit_logger.get_entries(limit=10000)
        entry_map = {e["id"]: e for e in entries}
        
        # Build lineage chain
        while current_id and current_id in entry_map:
            entry = entry_map[current_id]
            lineage.append({
                "id": entry["id"],
                "timestamp": entry["timestamp"],
                "action": entry["action"],
                "user_role": entry["user_role"],
                "prev_hash": entry["prev_hash"],
                "entry_hash": entry["entry_hash"]
            })
            current_id = entry.get("prev_entry_id")
        
        lineage.reverse()
        return lineage

    def generate_audit_report(
        self,
        start_id: Optional[int] = None,
        end_id: Optional[int] = None,
        role_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive audit report.
        
        Args:
            start_id: Starting entry ID (oldest)
            end_id: Ending entry ID (newest)
            role_filter: Filter by user role
        
        Returns:
            Audit report with statistics and integrity status
        """
        entries = self.audit_logger.get_entries(limit=10000)
        
        if role_filter:
            entries = [e for e in entries if e["user_role"] == role_filter]
        
        if start_id:
            entries = [e for e in entries if e["id"] >= start_id]
        if end_id:
            entries = [e for e in entries if e["id"] <= end_id]
        
        # Statistics
        action_counts = {}
        role_counts = {}
        for entry in entries:
            action = entry.get("action", "unknown")
            role = entry.get("user_role", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1
            role_counts[role] = role_counts.get(role, 0) + 1
        
        # Chain integrity
        chain_status = self.verify_chain()
        
        return {
            "report_generated_at": "now",  # Would use datetime
            "total_entries": len(entries),
            "start_entry_id": entries[-1]["id"] if entries else None,
            "end_entry_id": entries[0]["id"] if entries else None,
            "action_statistics": action_counts,
            "role_statistics": role_counts,
            "chain_integrity": chain_status,
            "filters_applied": {
                "role": role_filter,
                "start_id": start_id,
                "end_id": end_id
            }
        }