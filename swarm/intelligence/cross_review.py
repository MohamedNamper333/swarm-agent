"""
Cross-Review Module - Multi-Agent Review Coordination
Implements peer review, adversarial review, and consensus resolution
"""
import json
import logging
import threading
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReviewVerdict(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"
    NEEDS_INFO = "needs_info"


class ReviewType(str, Enum):
    PEER_REVIEW = "peer_review"
    ADVERSARIAL = "adversarial"
    CONSENSUS = "consensus"
    SECURITY_AUDIT = "security_audit"
    ARCHITECTURE_REVIEW = "architecture_review"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


@dataclass
class ReviewCriteria:
    name: str
    description: str
    weight: float
    required: bool
    threshold: float = 0.8


@dataclass
class ReviewFinding:
    id: str = ""
    criterion: str = ""
    severity: str = "medium"
    title: str = ""
    description: str = ""
    location: str = ""
    suggestion: str = ""
    confidence: float = 0.8


@dataclass
class ReviewVerdictResult:
    verdict: ReviewVerdict
    confidence: float
    findings: List[Dict] = field(default_factory=list)
    summary: str = ""
    reviewer_notes: str = ""


@dataclass
class ReviewRequest:
    id: str
    artifact_id: str
    artifact_type: str
    artifact_content: str
    requester_id: str
    reviewer_ids: List[str]
    review_type: str
    criteria: List[ReviewCriteria] = field(default_factory=list)
    deadline: str = ""
    status: ReviewStatus = ReviewStatus.PENDING
    reviews: Dict[str, ReviewVerdictResult] = field(default_factory=dict)
    consensus: Optional[Dict] = None


class CrossReviewEngine:
    """Coordinates multi-agent reviews with consensus resolution."""

    DEFAULT_CRITERIA = {
        "correctness": ReviewCriteria(
            name="correctness",
            description="Code correctness and logical soundness",
            weight=1.0,
            required=True,
            threshold=0.8,
        ),
        "security": ReviewCriteria(
            name="security",
            description="Security vulnerabilities and exposure",
            weight=2.0,
            required=True,
            threshold=0.9,
        ),
        "performance": ReviewCriteria(
            name="performance",
            description="Performance and efficiency",
            weight=1.2,
            required=False,
            threshold=0.7,
        ),
        "maintainability": ReviewCriteria(
            name="maintainability",
            description="Maintainability and readability",
            weight=1.0,
            required=False,
            threshold=0.7,
        ),
        "architecture": ReviewCriteria(
            name="architecture",
            description="Architecture alignment and design",
            weight=1.2,
            required=False,
            threshold=0.7,
        ),
        "testing": ReviewCriteria(
            name="testing",
            description="Test coverage and test quality",
            weight=1.0,
            required=False,
            threshold=0.7,
        ),
        "documentation": ReviewCriteria(
            name="documentation",
            description="Documentation completeness",
            weight=0.8,
            required=False,
            threshold=0.6,
        ),
        "constitutional": ReviewCriteria(
            name="constitutional",
            description="Alignment with constitutional principles",
            weight=1.5,
            required=True,
            threshold=0.9,
        ),
    }

    ADVERSARIAL_PROMPTS = {
        "security": [
            "How would you attack this code?",
            "Where could injection or tampering occur?",
            "What secrets or credentials are exposed?",
            "How could authentication or authorization be bypassed?",
            "Where is input validation missing?",
            "What happens if this runs with elevated privileges?",
        ],
        "correctness": [
            "Where could this fail silently?",
            "What edge cases are unhandled?",
            "Where are race conditions or ordering bugs possible?",
            "What happens on empty, null, or malformed input?",
            "Where is error handling missing?",
        ],
        "architecture": [
            "Where does this violate layering or boundaries?",
            "What coupling is introduced?",
            "How does this scale under load?",
            "Where should this be decomposed?",
            "What invariants or contracts are broken?",
        ],
        "maintainability": [
            "Where is logic duplicated?",
            "What makes this hard to test?",
            "Where are names misleading?",
            "What complexity is unjustified?",
            "How easily can this be extended?",
        ],
    }

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or "data/cross_reviews")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.review_file = self.storage_path / "reviews.json"
        self.reviews: Dict[str, ReviewRequest] = {}
        self._lock = threading.RLock()
        self._load()

    def _new_id(self) -> str:
        return f"rev_{int(time.time() * 1000)}_{len(self.reviews)}"

    def _load(self) -> None:
        if not self.review_file.exists():
            return
        try:
            raw = json.loads(self.review_file.read_text())
            for item in raw:
                review = self._deserialize_review(item)
                if review is not None:
                    self.reviews[review.id] = review
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load cross-review state: %s", exc)

    def _save(self) -> None:
        try:
            payload = [self._serialize_review(r) for r in self.reviews.values()]
            self.review_file.write_text(json.dumps(payload, indent=2))
        except OSError as exc:
            logger.warning("Failed to persist cross-review state: %s", exc)

    @staticmethod
    def _serialize_review(review: ReviewRequest) -> Dict[str, Any]:
        return {
            "id": review.id,
            "artifact_id": review.artifact_id,
            "artifact_type": review.artifact_type,
            "artifact_content": review.artifact_content,
            "requester_id": review.requester_id,
            "reviewer_ids": list(review.reviewer_ids),
            "review_type": (
                review.review_type.value
                if isinstance(review.review_type, Enum)
                else review.review_type
            ),
            "criteria": [asdict(c) for c in review.criteria],
            "deadline": review.deadline,
            "status": (
                review.status.value if isinstance(review.status, Enum) else review.status
            ),
            "reviews": {
                reviewer_id: asdict(result) for reviewer_id, result in review.reviews.items()
            },
            "consensus": review.consensus,
        }

    @classmethod
    def _deserialize_review(cls, item: Dict[str, Any]) -> Optional[ReviewRequest]:
        try:
            reviews = {}
            for reviewer_id, result in item.get("reviews", {}).items():
                reviews[reviewer_id] = ReviewVerdictResult(
                    verdict=ReviewVerdict(result.get("verdict", "approve")),
                    confidence=float(result.get("confidence", 0.8)),
                    findings=list(result.get("findings", [])),
                    summary=result.get("summary", ""),
                    reviewer_notes=result.get("reviewer_notes", ""),
                )
            criteria = [ReviewCriteria(**c) for c in item.get("criteria", [])]
            return ReviewRequest(
                id=item["id"],
                artifact_id=item["artifact_id"],
                artifact_type=item.get("artifact_type", "code"),
                artifact_content=item.get("artifact_content", ""),
                requester_id=item["requester_id"],
                reviewer_ids=list(item.get("reviewer_ids", [])),
                review_type=ReviewType(item.get("review_type", "peer_review")),
                criteria=criteria,
                deadline=item.get("deadline", ""),
                status=ReviewStatus(item.get("status", "pending")),
                reviews=reviews,
                consensus=item.get("consensus"),
            )
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Skipping malformed review record: %s", exc)
            return None

    def request_review(
        self,
        artifact_id: str,
        artifact_type: str,
        artifact_content: str,
        requester_id: str,
        reviewer_ids: List[str],
        review_type: ReviewType = ReviewType.PEER_REVIEW,
        deadline_hours: int = 24,
        criteria_names: Optional[List[str]] = None,
    ) -> str:
        with self._lock:
            review_id = self._new_id()
            names = criteria_names or list(self.DEFAULT_CRITERIA.keys())
            criteria = [self.DEFAULT_CRITERIA[n] for n in names if n in self.DEFAULT_CRITERIA]
            review = ReviewRequest(
                id=review_id,
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                artifact_content=artifact_content,
                requester_id=requester_id,
                reviewer_ids=list(reviewer_ids),
                review_type=review_type,
                criteria=criteria,
                deadline=(datetime.now() + timedelta(hours=deadline_hours)).isoformat(),
                status=ReviewStatus.PENDING,
            )
            self.reviews[review_id] = review
            self._save()
            logger.info("Review %s requested by %s for artifact %s", review_id, requester_id, artifact_id)
            return review_id

    def run_adversarial_review(
        self,
        artifact_id: str,
        artifact_content: str,
        artifact_type: str = "code",
        defender_id: str = "system",
        attacker_ids: Optional[List[str]] = None,
        focus_areas: Optional[List[str]] = None,
        deadline_hours: int = 24,
    ) -> str:
        reviewers = list(attacker_ids) if attacker_ids else []
        review_id = self.request_review(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            artifact_content=artifact_content,
            requester_id=defender_id,
            reviewer_ids=reviewers,
            review_type=ReviewType.ADVERSARIAL,
            deadline_hours=deadline_hours,
            criteria_names=focus_areas,
        )
        logger.info("Adversarial review %s requested (defender=%s)", review_id, defender_id)
        return review_id

    def submit_review(
        self,
        review_id: str,
        reviewer_id: str,
        verdict: str,
        findings: Optional[List[Dict]] = None,
        confidence: float = 0.8,
        summary: str = "",
        notes: str = "",
    ) -> bool:
        with self._lock:
            review = self.reviews.get(review_id)
            if review is None:
                logger.warning("submit_review: unknown review %s", review_id)
                return False
            if reviewer_id not in review.reviewer_ids:
                logger.warning("submit_review: %s is not a reviewer on %s", reviewer_id, review_id)
                return False
            try:
                verdict_enum = ReviewVerdict(verdict)
            except ValueError:
                logger.warning("submit_review: invalid verdict %r", verdict)
                return False
            review.reviews[reviewer_id] = ReviewVerdictResult(
                verdict=verdict_enum,
                confidence=float(confidence),
                findings=[dict(f) for f in (findings or [])],
                summary=summary,
                reviewer_notes=notes,
            )
            if review.status == ReviewStatus.PENDING:
                review.status = ReviewStatus.IN_PROGRESS
            if len(review.reviews) >= len(review.reviewer_ids):
                self._resolve_consensus(review)
            self._save()
            return True

    def _resolve_consensus(self, review: ReviewRequest) -> None:
        verdicts = [r.verdict for r in review.reviews.values()]
        total = max(len(verdicts), 1)
        approve_count = verdicts.count(ReviewVerdict.APPROVE)
        agreement = round(approve_count / total, 4)

        blockers = [
            finding
            for r in review.reviews.values()
            if r.verdict == ReviewVerdict.REJECT
            for finding in r.findings
        ]

        if ReviewVerdict.REJECT in verdicts:
            verdict = "reject"
        elif ReviewVerdict.REQUEST_CHANGES in verdicts:
            verdict = "changes_requested"
        else:
            verdict = "approve"

        review.consensus = {
            "verdict": verdict,
            "agreement": agreement,
            "reviewers": len(verdicts),
            "blockers": blockers,
            "resolved_at": datetime.now().isoformat(),
        }
        review.status = ReviewStatus.COMPLETED
        logger.info("Review %s resolved: %s (agreement=%.2f)", review.id, verdict, agreement)

    def get_pending_reviews(self, reviewer_id: str) -> List[ReviewRequest]:
        with self._lock:
            return [
                r
                for r in self.reviews.values()
                if reviewer_id in r.reviewer_ids
                and reviewer_id not in r.reviews
                and r.status in (ReviewStatus.PENDING, ReviewStatus.IN_PROGRESS)
            ]

    def get_review_status(self, review_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            review = self.reviews.get(review_id)
            if review is None:
                return None
            return {
                "id": review.id,
                "artifact_id": review.artifact_id,
                "artifact_type": review.artifact_type,
                "requester_id": review.requester_id,
                "status": review.status.value if isinstance(review.status, Enum) else review.status,
                "reviewers_total": len(review.reviewer_ids),
                "reviews_submitted": len(review.reviews),
                "deadline": review.deadline,
                "consensus": review.consensus,
            }

    def get_review(self, review_id: str) -> Optional[ReviewRequest]:
        with self._lock:
            return self.reviews.get(review_id)

    def get_agent_stats(self, agent_id: str) -> Dict[str, int]:
        with self._lock:
            reviews_given = 0
            reviews_received = 0
            for review in self.reviews.values():
                if review.requester_id == agent_id:
                    reviews_received += 1
                if agent_id in review.reviews:
                    reviews_given += 1
            return {
                "reviews_given": reviews_given,
                "reviews_received": reviews_received,
                "reviews_pending": len(self.get_pending_reviews(agent_id)),
            }

    def get_review_analytics(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self.reviews)
            pending = sum(
                1
                for r in self.reviews.values()
                if r.status in (ReviewStatus.PENDING, ReviewStatus.IN_PROGRESS)
            )
            verdict_distribution: Dict[str, int] = defaultdict(int)
            for r in self.reviews.values():
                if r.consensus is not None:
                    verdict_distribution[r.consensus.get("verdict", "pending")] += 1
                else:
                    verdict_distribution["pending"] += 1
            return {
                "total_reviews": total,
                "pending": pending,
                "completed": total - pending,
                "verdict_distribution": dict(verdict_distribution),
                "blockers_total": sum(
                    len(r.consensus.get("blockers", []))
                    for r in self.reviews.values()
                    if r.consensus
                ),
            }

    def escalate_review(self, review_id: str, reason: str = "") -> bool:
        with self._lock:
            review = self.reviews.get(review_id)
            if review is None:
                return False
            review.status = ReviewStatus.ESCALATED
            review.consensus = {"verdict": "escalated", "reason": reason, "escalated_at": datetime.now().isoformat()}
            self._save()
            return True


def create_cross_review_engine(storage_path: Optional[str] = None) -> CrossReviewEngine:
    """Factory for CrossReviewEngine."""
    return CrossReviewEngine(storage_path=storage_path)
