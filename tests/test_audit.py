# tests/test_audit.py
"""Tests for the audit logger."""

import pytest
import tempfile
import os
import sqlite3
from datetime import datetime

from src.audit.logger import AuditLogger
from src.audit.verifier import AuditVerifier


class TestAuditLogger:
    """Tests for the audit logger."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_init_schema(self, temp_db):
        """Test database schema initialization."""
        logger = AuditLogger(temp_db)
        
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        assert "audit_log" in tables

    def test_log_entry(self, temp_db):
        """Test logging an entry."""
        logger = AuditLogger(temp_db)
        
        entry_id = logger.log(
            role="analyst",
            action="query",
            query="Show districts with low utilization",
            result={"count": 5}
        )
        
        assert entry_id == 1
        
        entries = logger.get_entries()
        assert len(entries) == 1
        assert entries[0]["user_role"] == "analyst"
        assert entries[0]["action"] == "query"

    def test_hash_computation(self, temp_db):
        """Test that hashes are computed correctly."""
        logger = AuditLogger(temp_db)
        
        logger.log(
            role="policymaker",
            action="export",
            query="Export report"
        )
        
        entries = logger.get_entries()
        entry = entries[0]
        
        assert entry["query_hash"] is not None
        assert len(entry["query_hash"]) == 64  # SHA-256 hex
        assert entry["entry_hash"] is not None

    def test_hash_chain(self, temp_db):
        """Test hash chain linking."""
        logger = AuditLogger(temp_db)
        
        id1 = logger.log(role="analyst", action="query", query="Query 1")
        id2 = logger.log(role="analyst", action="query", query="Query 2")
        
        entries = logger.get_entries()
        
        assert entries[0]["prev_hash"] is not None  # id2 links to id1
        assert entries[1]["prev_hash"] is None  # id1 is genesis

    def test_chain_integrity_valid(self, temp_db):
        """Test chain integrity verification with valid chain."""
        logger = AuditLogger(temp_db)
        
        for i in range(3):
            logger.log(role="analyst", action=f"query_{i}", query=f"Query {i}")
        
        verification = logger.verify_chain_integrity()
        
        assert verification["valid"] is True
        assert verification["entries_checked"] == 3

    def test_get_entries_with_filter(self, temp_db):
        """Test filtering entries by role."""
        logger = AuditLogger(temp_db)
        
        logger.log(role="analyst", action="query", query="Q1")
        logger.log(role="policymaker", action="export", query="Q2")
        logger.log(role="analyst", action="query", query="Q3")
        
        analyst_entries = logger.get_entries(role_filter="analyst")
        assert len(analyst_entries) == 2
        
        policymaker_entries = logger.get_entries(role_filter="policymaker")
        assert len(policymaker_entries) == 1

    def test_count_entries(self, temp_db):
        """Test entry count."""
        logger = AuditLogger(temp_db)
        
        assert logger.count_entries() == 0
        
        logger.log(role="analyst", action="query", query="Q1")
        logger.log(role="analyst", action="query", query="Q2")
        
        assert logger.count_entries() == 2


class TestAuditVerifier:
    """Tests for the audit verifier."""

    @pytest.fixture
    def verifier_setup(self):
        """Set up audit logger and verifier for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        logger = AuditLogger(db_path)
        verifier = AuditVerifier(logger)
        
        logger.log(role="analyst", action="query", query="Test query")
        
        yield verifier, logger, db_path
        
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_verify_entry(self, verifier_setup):
        """Test single entry verification."""
        verifier, logger, _ = verifier_setup
        
        result = verifier.verify_entry(1)
        
        assert result["valid"] is True
        assert result["entry_id"] == 1

    def test_verify_query_hash(self, verifier_setup):
        """Test query hash verification."""
        verifier, _, _ = verifier_setup
        
        result = verifier.verify_query_hash(1, "Test query")
        
        assert result["valid"] is True
        assert result["match"] is True

    def test_verify_query_hash_mismatch(self, verifier_setup):
        """Test query hash mismatch detection."""
        verifier, _, _ = verifier_setup
        
        result = verifier.verify_query_hash(1, "Modified query")
        
        assert result["valid"] is False
        assert result["match"] is False