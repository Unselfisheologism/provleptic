# src/compliance/dpdp.py
"""
DPDP Act 2023 Compliance Module for Policy Intelligence System.

Implements key principles:
- Purpose Limitation (Section 4): Data collected only for specified purposes
- Data Minimization (Section 6): Only collect data necessary for purpose
- Retention Policy (Section 9): Delete data when purpose is served
- Consent Framework (Sections 6-8): Consent must be explicit and purpose-driven
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from loguru import logger


class Purpose(Enum):
    """Defined purposes for data processing under DPDP."""
    POLICY_ANALYSIS = "policy_analysis"
    DISTRICT_REVIEW = "district_review"
    FUND_UTILIZATION = "fund_utilization"
    SCHEME_MONITORING = "scheme_monitoring"
    PUBLIC_INQUIRY = "public_inquiry"
    RESEARCH = "research"


@dataclass
class DataField:
    """Represents a data field with sensitivity classification."""
    name: str
    purpose: Purpose
    is_pii: bool = False
    is_sensitive: bool = False
    retention_days: Optional[int] = None


@dataclass
class RetentionEntry:
    """Record of data retention."""
    data_id: str
    purpose: Purpose
    ingested_at: datetime
    retention_until: Optional[datetime]
    purpose_served: bool = False


class DataMinimizer:
    """
    Implements data minimization per DPDP Section 6.
    
    Only fields relevant to the specified purpose are retained.
    """

    # Purpose-to-field mapping
    PURPOSE_FIELDS: Dict[Purpose, Set[str]] = {
        Purpose.POLICY_ANALYSIS: {
            "district", "state", "scheme", "utilization_percent",
            "population", "target", "achieved", "outcome"
        },
        Purpose.DISTRICT_REVIEW: {
            "district", "state", "pmay_utilization_percent",
            "population", "funds_allocated", "funds_utilized", "review_status"
        },
        Purpose.FUND_UTILIZATION: {
            "district", "scheme", "funds_allocated", "funds_utilized",
            "utilization_percent", "quarter", "fiscal_year"
        },
        Purpose.SCHEME_MONITORING: {
            "scheme", "ministry", "state", "target", "achieved",
            "coverage_percent", "beneficiaries"
        },
        Purpose.PUBLIC_INQUIRY: {
            "scheme", "eligibility", "benefits", "application_process",
            "contact_info", "state"
        },
        Purpose.RESEARCH: {
            "district", "state", "scheme", "aggregate_metrics",
            "anonymized_metrics"
        }
    }

    def minimize(self, data: Dict, purpose: Purpose) -> Dict:
        """
        Minimize data to only fields relevant for the purpose.
        
        Args:
            data: Input data dictionary
            purpose: The purpose for data processing
        
        Returns:
            Minimized data dictionary
        """
        allowed_fields = self.PURPOSE_FIELDS.get(purpose, set())
        
        minimized = {}
        for key, value in data.items():
            # Normalize key for matching
            normalized_key = key.lower().replace(" ", "_")
            normalized_allowed = [f.lower() for f in allowed_fields]
            
            if any(field in normalized_key for field in normalized_allowed):
                minimized[key] = value
            elif key in allowed_fields:
                minimized[key] = value
        
        # Always remove potential PII fields unless explicitly needed
        pii_fields = {"aadhaar", "pan", "phone", "email", "address", "name"}
        for pii in pii_fields:
            minimized.pop(pii, None)
            minimized.pop(f"{pii}_number", None)
            minimized.pop(f"{pii}_id", None)
        
        logger.info(f"Data minimized for purpose {purpose.value}: {len(minimized)} fields retained")
        return minimized

    def get_relevant_fields(self, purpose: Purpose) -> List[str]:
        """Get list of relevant fields for a purpose."""
        return list(self.PURPOSE_FIELDS.get(purpose, set()))


class PurposeLimiter:
    """
    Implements purpose limitation per DPDP Section 4.
    
    Ensures data is only used for the purpose it was collected for.
    """

    def __init__(self):
        self.data_purposes: Dict[str, Purpose] = {}

    def mark_purpose(self, data_id: str, purpose: Purpose) -> None:
        """Mark data with its intended purpose."""
        self.data_purposes[data_id] = purpose
        logger.info(f"Data {data_id} marked for purpose: {purpose.value}")

    def verify_purpose(self, data_id: str, intended_purpose: Purpose) -> bool:
        """
        Verify data is being used for its intended purpose.
        
        Args:
            data_id: Unique identifier of the data
            intended_purpose: The purpose data is being used for
        
        Returns:
            True if purpose matches, False if purpose mismatch
        """
        original_purpose = self.data_purposes.get(data_id)
        
        if original_purpose is None:
            logger.warning(f"Data {data_id} has no marked purpose")
            return True  # Allow if not marked
        
        if original_purpose != intended_purpose:
            logger.warning(
                f"Purpose mismatch for {data_id}: "
                f"original={original_purpose.value}, intended={intended_purpose.value}"
            )
            return False
        
        return True

    def get_purpose(self, data_id: str) -> Optional[Purpose]:
        """Get the marked purpose for data."""
        return self.data_purposes.get(data_id)


class RetentionPolicy:
    """
    Implements retention policy per DPDP Section 9.
    
    Data should be deleted when purpose is served.
    """

    DEFAULT_RETENTION_DAYS = {
        Purpose.POLICY_ANALYSIS: 365,
        Purpose.DISTRICT_REVIEW: 180,
        Purpose.FUND_UTILIZATION: 730,
        Purpose.SCHEME_MONITORING: 365,
        Purpose.PUBLIC_INQUIRY: 90,
        Purpose.RESEARCH: 1825,
    }

    def __init__(self, custom_retention: Optional[Dict[Purpose, int]] = None):
        self.retention_days = custom_retention or self.DEFAULT_RETENTION_DAYS
        self.retention_records: Dict[str, RetentionEntry] = {}

    def create_entry(
        self,
        data_id: str,
        purpose: Purpose,
        custom_retention_days: Optional[int] = None
    ) -> RetentionEntry:
        """Create a retention record for data."""
        retention_days = custom_retention_days or self.retention_days.get(
            purpose, 365
        )
        ingested_at = datetime.utcnow()
        retention_until = ingested_at + timedelta(days=retention_days)
        
        entry = RetentionEntry(
            data_id=data_id,
            purpose=purpose,
            ingested_at=ingested_at,
            retention_until=retention_until
        )
        
        self.retention_records[data_id] = entry
        logger.info(f"Retention entry created for {data_id}: expires {retention_until}")
        return entry

    def should_delete(self, data_id: str) -> bool:
        """
        Check if data should be deleted based on retention policy.
        
        Args:
            data_id: Unique identifier of the data
        
        Returns:
            True if data should be deleted
        """
        entry = self.retention_records.get(data_id)
        
        if entry is None:
            logger.info(f"No retention record for {data_id}, applying default")
            return False
        
        if entry.purpose_served:
            return True
        
        if datetime.utcnow() > entry.retention_until:
            return True
        
        return False

    def mark_purpose_served(self, data_id: str) -> None:
        """Mark that purpose has been served, data can be deleted."""
        if data_id in self.retention_records:
            self.retention_records[data_id].purpose_served = True
            logger.info(f"Purpose served for {data_id}, marked for deletion")

    def get_retention_info(self, data_id: str) -> Optional[Dict]:
        """Get retention information for data."""
        entry = self.retention_records.get(data_id)
        
        if entry is None:
            return None
        
        return {
            "data_id": entry.data_id,
            "purpose": entry.purpose.value,
            "ingested_at": entry.ingested_at.isoformat(),
            "retention_until": entry.retention_until.isoformat() if entry.retention_until else None,
            "purpose_served": entry.purpose_served,
            "should_delete": self.should_delete(data_id)
        }


class DPDPChecker:
    """
    Main DPDP compliance checker.
    
    Orchestrates purpose limitation, data minimization, and retention policies.
    """

    def __init__(self):
        self.purpose_limiter = PurposeLimiter()
        self.data_minimizer = DataMinimizer()
        self.retention_policy = RetentionPolicy()

    def minimize_data(
        self,
        data: Dict,
        purpose: Purpose,
        data_id: Optional[str] = None
    ) -> Dict:
        """
        Apply data minimization for a specific purpose.
        
        Args:
            data: Input data
            purpose: Processing purpose
            data_id: Optional data identifier
        
        Returns:
            Minimized data
        """
        if data_id:
            self.purpose_limiter.mark_purpose(data_id, purpose)
            self.retention_policy.create_entry(data_id, purpose)
        
        return self.data_minimizer.minimize(data, purpose)

    def verify_access(
        self,
        data_id: str,
        purpose: Purpose
    ) -> bool:
        """Verify data access is compliant with purpose."""
        return self.purpose_limiter.verify_purpose(data_id, purpose)

    def check_retention(self, data_id: str) -> bool:
        """Check if data should be deleted due to retention policy."""
        return self.retention_policy.should_delete(data_id)

    def get_compliance_report(self, data_ids: List[str]) -> Dict:
        """
        Generate compliance report for data IDs.
        
        Args:
            data_ids: List of data IDs to check
        
        Returns:
            Compliance report with retention status
        """
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "total_checked": len(data_ids),
            "deletions_required": 0,
            "within_retention": 0,
            "items": []
        }
        
        for data_id in data_ids:
            retention_info = self.retention_policy.get_retention_info(data_id)
            purpose = self.purpose_limiter.get_purpose(data_id)
            
            item = {
                "data_id": data_id,
                "purpose": purpose.value if purpose else "unknown",
                "retention": retention_info,
                "deletion_required": self.check_retention(data_id)
            }
            report["items"].append(item)
            
            if item["deletion_required"]:
                report["deletions_required"] += 1
            else:
                report["within_retention"] += 1
        
        return report