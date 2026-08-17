"""
Data Classification — F-035: Missing Data Classification fix.

Classification: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED, PII, SECRET.
Policy per classification.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set, Callable, Pattern
from enum import Enum
import re
import threading
import logging

logger = logging.getLogger(__name__)


class DataClassification(str, Enum):
    """Data classification levels (ordered by sensitivity)."""
    PUBLIC = "public"           # Safe for public disclosure
    INTERNAL = "internal"       # Internal use only
    CONFIDENTIAL = "confidential"  # Limited access
    RESTRICTED = "restricted"   # Need-to-know basis
    PII = "pii"                 # Personally identifiable information
    SECRET = "secret"           # Highest sensitivity

    def __lt__(self, other):
        """Compare sensitivity levels."""
        order = {
            DataClassification.PUBLIC: 0,
            DataClassification.INTERNAL: 1,
            DataClassification.CONFIDENTIAL: 2,
            DataClassification.RESTRICTED: 3,
            DataClassification.PII: 4,
            DataClassification.SECRET: 5,
        }
        return order[self] < order.get(other, 0)

    def __le__(self, other):
        return self == other or self < other


class ClassificationRule:
    """Rule for automatic classification."""

    def __init__(
        self,
        classification: DataClassification,
        patterns: List[Pattern] = None,
        keywords: List[str] = None,
        field_names: List[str] = None,
        min_confidence: float = 0.8,
    ):
        self.classification = classification
        self.patterns = patterns or []
        self.keywords = [k.lower() for k in (keywords or [])]
        self.field_names = [f.lower() for f in (field_names or [])]
        self.min_confidence = min_confidence


class DataClassifier:
    """Classifies data based on rules and content analysis."""

    DEFAULT_RULES = [
        ClassificationRule(
            DataClassification.SECRET,
            patterns=[
                re.compile(r"api[_-]?key", re.I),
                re.compile(r"secret[_-]?key", re.I),
                re.compile(r"private[_-]?key", re.I),
                re.compile(r"password", re.I),
                re.compile(r"token", re.I),
            ],
            keywords=["secret", "password", "token", "credential"],
            field_names=["password", "secret", "token", "api_key", "private_key"],
        ),
        ClassificationRule(
            DataClassification.PII,
            patterns=[
                re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN
                re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),  # Credit card
                re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # Email
                re.compile(r"\b\d{3}[\s-]?\d{3}[\s-]?\d{4}\b"),  # Phone
            ],
            keywords=["ssn", "social security", "credit card", "email", "phone", "address", "date of birth"],
            field_names=["ssn", "email", "phone", "address", "dob", "date_of_birth"],
        ),
        ClassificationRule(
            DataClassification.RESTRICTED,
            patterns=[
                re.compile(r"confidential", re.I),
                re.compile(r"proprietary", re.I),
                re.compile(r"internal[_-]?only", re.I),
            ],
            keywords=["confidential", "proprietary", "internal only", "classified"],
            field_names=["internal_notes", "restricted_data"],
        ),
        ClassificationRule(
            DataClassification.CONFIDENTIAL,
            patterns=[
                re.compile(r"confidential", re.I),
                re.compile(r"business[_-]?secret", re.I),
            ],
            keywords=["confidential", "business secret", "trade secret"],
            field_names=["confidential_data", "business_plan"],
        ),
        ClassificationRule(
            DataClassification.INTERNAL,
            patterns=[
                re.compile(r"internal", re.I),
            ],
            keywords=["internal", "staff only", "employee only"],
            field_names=["internal_memo", "staff_notes"],
        ),
    ]

    def __init__(self, custom_rules: List[ClassificationRule] = None):
        self._rules = self.DEFAULT_RULES + (custom_rules or [])

    def classify(self, data: Any, field_name: str = "") -> DataClassification:
        """Classify data based on content and field name."""
        if data is None:
            return DataClassification.INTERNAL

        text = str(data).lower()
        field_lower = field_name.lower()

        # Check field name first (highest confidence)
        for rule in self._rules:
            if field_lower in rule.field_names:
                return rule.classification

        # Check patterns
        for rule in self._rules:
            for pattern in rule.patterns:
                if pattern.search(text):
                    return rule.classification

        # Check keywords
        for rule in self._rules:
            for keyword in rule.keywords:
                if keyword in text:
                    return rule.classification

        return DataClassification.INTERNAL

    def classify_dict(self, data: Dict[str, Any]) -> Dict[str, DataClassification]:
        """Classify all fields in a dict."""
        return {k: self.classify(v, k) for k, v in data.items()}

    def get_highest_classification(self, data: Dict[str, Any]) -> DataClassification:
        """Get highest classification across all fields."""
        classifications = self.classify_dict(data).values()
        return max(classifications) if classifications else DataClassification.INTERNAL


class DataClassificationPolicy:
    """Policy enforcement based on classification."""

    DEFAULT_POLICIES = {
        DataClassification.PUBLIC: {
            "encryption_required": False,
            "access_logging": False,
            "retention_days": 2555,  # 7 years
            "allowed_transport": ["http", "https", "email"],
            "allowed_storage": ["public_cloud", "cdn"],
        },
        DataClassification.INTERNAL: {
            "encryption_required": True,
            "encryption_algorithm": "AES-256",
            "access_logging": True,
            "retention_days": 2555,
            "allowed_transport": ["https", "sftp"],
            "allowed_storage": ["private_cloud", "on_premise"],
        },
        DataClassification.CONFIDENTIAL: {
            "encryption_required": True,
            "encryption_algorithm": "AES-256",
            "access_logging": True,
            "audit_access": True,
            "retention_days": 3650,  # 10 years
            "allowed_transport": ["https", "sftp", "mtls"],
            "allowed_storage": ["encrypted_private_cloud", "hsm"],
        },
        DataClassification.RESTRICTED: {
            "encryption_required": True,
            "encryption_algorithm": "AES-256",
            "access_logging": True,
            "audit_access": True,
            "approval_required": True,
            "retention_days": 3650,
            "allowed_transport": ["mtls", "dedicated_line"],
            "allowed_storage": ["hsm", "air_gapped"],
        },
        DataClassification.PII: {
            "encryption_required": True,
            "encryption_algorithm": "AES-256",
            "access_logging": True,
            "audit_access": True,
            "consent_required": True,
            "retention_days": 1095,  # 3 years (GDPR)
            "allowed_transport": ["https", "mtls"],
            "allowed_storage": ["encrypted_private_cloud", "eu_region_only"],
            "right_to_erasure": True,
        },
        DataClassification.SECRET: {
            "encryption_required": True,
            "encryption_algorithm": "AES-256",
            "access_logging": True,
            "audit_access": True,
            "approval_required": True,
            "dual_control": True,
            "retention_days": 3650,
            "allowed_transport": ["mtls", "dedicated_line", "courier"],
            "allowed_storage": ["hsm", "air_gapped"],
            "key_rotation_days": 90,
        },
    }

    def __init__(self, custom_policies: Dict[DataClassification, Dict] = None):
        self._policies = {**self.DEFAULT_POLICIES, **(custom_policies or {})}

    def get_policy(self, classification: DataClassification) -> Dict[str, Any]:
        return self._policies.get(classification, self.DEFAULT_POLICIES[DataClassification.INTERNAL])

    def is_transport_allowed(self, classification: DataClassification, transport: str) -> bool:
        policy = self.get_policy(classification)
        return transport in policy.get("allowed_transport", [])

    def is_storage_allowed(self, classification: DataClassification, storage: str) -> bool:
        policy = self.get_policy(classification)
        return storage in policy.get("allowed_storage", [])

    def requires_encryption(self, classification: DataClassification) -> bool:
        policy = self.get_policy(classification)
        return policy.get("encryption_required", True)

    def get_retention_days(self, classification: DataClassification) -> int:
        policy = self.get_policy(classification)
        return policy.get("retention_days", 365)


# Global instances
_classifier: Optional[DataClassifier] = None
_policy: Optional[DataClassificationPolicy] = None
_dc_lock = threading.Lock()
_dp_lock = threading.Lock()


def get_data_classifier() -> DataClassifier:
    global _classifier
    with _dc_lock:
        if _classifier is None:
            _classifier = DataClassifier()
        return _classifier


def get_classification_policy() -> DataClassificationPolicy:
    global _policy
    with _dp_lock:
        if _policy is None:
            _policy = DataClassificationPolicy()
        return _policy


def classify_data(data: Any, field_name: str = "") -> DataClassification:
    """Convenience function to classify data."""
    return get_data_classifier().classify(data, field_name)


def get_policy(classification: DataClassification) -> Dict[str, Any]:
    """Get policy for classification."""
    return get_classification_policy().get_policy(classification)


__all__ = [
    "DataClassification",
    "ClassificationRule",
    "DataClassifier",
    "DataClassificationPolicy",
    "get_data_classifier",
    "get_classification_policy",
    "classify_data",
    "get_policy",
]