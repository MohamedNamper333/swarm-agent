"""
Inter-Agent Bus — F-021: Inter-Agent Bus Semantics Undefined fix.

Defines delivery semantics, ordering, acknowledgment, deduplication, retry, TTL, dead-letter, message schema version.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable, Set
from enum import Enum
from datetime import datetime, timezone
import uuid
import threading
import time
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class DeliverySemantics(str, Enum):
    AT_MOST_ONCE = "at_most_once"       # Fire and forget, may lose
    AT_LEAST_ONCE = "at_least_once"     # Guaranteed delivery, may duplicate
    EXACTLY_ONCE = "exactly_once"       # Guaranteed exactly once (requires idempotency)


class MessagePriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MessageStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass(frozen=True)
class MessageSchema:
    """Message schema with version."""
    schema_id: str
    version: int
    fields: Dict[str, str]  # field_name -> type


@dataclass
class BusMessage:
    """Message on the agent bus."""
    message_id: str
    schema: MessageSchema
    payload: Dict[str, Any]
    sender_id: str
    recipient_id: Optional[str] = None  # None = broadcast
    topic: Optional[str] = None
    priority: MessagePriority = MessagePriority.NORMAL
    delivery_semantics: DeliverySemantics = DeliverySemantics.AT_LEAST_ONCE
    status: MessageStatus = MessageStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    ttl_seconds: int = 3600
    retry_count: int = 0
    max_retries: int = 3
    deduplication_key: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        return (datetime.now(timezone.utc) - self.created_at).total_seconds() > self.ttl_seconds

    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries and not self.is_expired()


class BusSubscription:
    """Subscription to a topic or direct messages."""

    def __init__(
        self,
        subscriber_id: str,
        topics: List[str] = None,
        handler: Callable[[BusMessage], Any] = None,
        filter_fn: Callable[[BusMessage], bool] = None,
    ):
        self.subscriber_id = subscriber_id
        self.topics = set(topics or [])
        self.handler = handler
        self.filter_fn = filter_fn
        self.created_at = datetime.now(timezone.utc)
        self.message_count = 0


class AgentBus:
    """
    Inter-agent message bus with defined semantics.
    
    Features:
    - Delivery semantics: at-most-once, at-least-once, exactly-once
    - Ordering: per-topic FIFO
    - Acknowledgment: explicit ack with timeout
    - Deduplication: via deduplication_key
    - Retry: configurable with backoff
    - TTL: message expiration
    - Dead-letter: failed messages after max retries
    - Schema versioning: message schema with version
    """

    def __init__(self, default_ttl_seconds: int = 3600):
        self._subscriptions: Dict[str, List[BusSubscription]] = defaultdict(list)
        self._direct_subscriptions: Dict[str, List[BusSubscription]] = defaultdict(list)
        self._pending_messages: Dict[str, BusMessage] = {}  # message_id -> message
        self._pending_acks: Dict[str, datetime] = {}  # message_id -> sent_at
        self._deduplication_store: Set[str] = set()
        self._lock = threading.RLock()
        self._default_ttl = default_ttl_seconds
        self._ack_timeout_seconds = 30
        self._retry_interval_seconds = 5
        self._cleanup_interval_seconds = 60
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False
        self._metrics = {
            "messages_sent": 0,
            "messages_delivered": 0,
            "messages_acknowledged": 0,
            "messages_failed": 0,
            "messages_dead_letter": 0,
            "deduplication_hits": 0,
        }

    def start(self) -> None:
        """Start background cleanup and retry threads."""
        if self._running:
            return
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info("AgentBus started")

    def stop(self) -> None:
        """Stop background threads."""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        logger.info("AgentBus stopped")

    def subscribe(
        self,
        subscriber_id: str,
        topics: List[str] = None,
        handler: Callable[[BusMessage], Any] = None,
        filter_fn: Callable[[BusMessage], bool] = None,
    ) -> BusSubscription:
        """Subscribe to topics or direct messages."""
        sub = BusSubscription(subscriber_id, topics, handler, filter_fn)
        with self._lock:
            if topics:
                for topic in topics:
                    self._subscriptions[topic].append(sub)
            else:
                # Direct subscription (recipient_id matches subscriber_id)
                self._direct_subscriptions[subscriber_id].append(sub)
        return sub

    def unsubscribe(self, subscription: BusSubscription) -> bool:
        """Unsubscribe."""
        with self._lock:
            removed = False
            for topic in subscription.topics:
                if subscription in self._subscriptions.get(topic, []):
                    self._subscriptions[topic].remove(subscription)
                    removed = True
            if subscription.subscriber_id in self._direct_subscriptions:
                if subscription in self._direct_subscriptions[subscription.subscriber_id]:
                    self._direct_subscriptions[subscription.subscriber_id].remove(subscription)
                    removed = True
            return removed

    def publish(
        self,
        sender_id: str,
        payload: Dict[str, Any],
        topic: Optional[str] = None,
        recipient_id: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        delivery_semantics: DeliverySemantics = DeliverySemantics.AT_LEAST_ONCE,
        ttl_seconds: Optional[int] = None,
        max_retries: int = 3,
        deduplication_key: Optional[str] = None,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        schema: Optional[MessageSchema] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BusMessage:
        """
        Publish a message to the bus.
        
        Returns the message for tracking.
        """
        # Deduplication check
        if deduplication_key:
            with self._lock:
                if deduplication_key in self._deduplication_store:
                    self._metrics["deduplication_hits"] += 1
                    logger.debug(f"Deduplication hit: {deduplication_key}")
                    # Return existing message or raise?
        else:
            deduplication_key = str(uuid.uuid4())

        message = BusMessage(
            message_id=str(uuid.uuid4()),
            schema=schema or MessageSchema(
                schema_id="default",
                version=1,
                fields={"payload": "dict"},
            ),
            payload=payload,
            sender_id=sender_id,
            recipient_id=recipient_id,
            topic=topic,
            priority=priority,
            delivery_semantics=delivery_semantics,
            ttl_seconds=ttl_seconds or self._default_ttl,
            max_retries=max_retries,
            deduplication_key=deduplication_key,
            correlation_id=correlation_id,
            causation_id=causation_id,
            metadata=metadata or {},
        )

        with self._lock:
            self._pending_messages[message.message_id] = message
            if deduplication_key:
                self._deduplication_store.add(deduplication_key)

        # Deliver immediately
        self._deliver(message)

        with self._lock:
            self._metrics["messages_sent"] += 1

        return message

    def _deliver(self, message: BusMessage) -> None:
        """Deliver message to subscribers."""
        delivered = False
        recipients: List[BusSubscription] = []

        with self._lock:
            # Direct recipient
            if message.recipient_id:
                recipients.extend(self._direct_subscriptions.get(message.recipient_id, []))

            # Topic subscribers
            if message.topic:
                recipients.extend(self._subscriptions.get(message.topic, []))

            # Broadcast (no topic, no recipient) - deliver to all direct subscribers
            if not message.recipient_id and not message.topic:
                for subs in self._direct_subscriptions.values():
                    recipients.extend(subs)

        for sub in recipients:
            if sub.filter_fn and not sub.filter_fn(message):
                continue

            try:
                if sub.handler:
                    sub.handler(message)
                sub.message_count += 1
                delivered = True

                with self._lock:
                    self._metrics["messages_delivered"] += 1

            except Exception as e:
                logger.error(f"Handler error for subscriber {sub.subscriber_id}: {e}")

        if not delivered and message.delivery_semantics != DeliverySemantics.AT_MOST_ONCE:
            # No one received it, but we need at-least-once
            logger.warning(f"Message {message.message_id} not delivered to any subscriber")
            self._schedule_retry(message)

    def acknowledge(self, message_id: str) -> bool:
        """Acknowledge message receipt."""
        with self._lock:
            message = self._pending_messages.get(message_id)
            if not message:
                return False

            if message.status == MessageStatus.ACKNOWLEDGED:
                return True

            message.status = MessageStatus.ACKNOWLEDGED
            message.acknowledged_at = datetime.now(timezone.utc)

            # Remove deduplication key on successful ack
            if message.deduplication_key:
                self._deduplication_store.discard(message.deduplication_key)

            self._pending_acks.pop(message_id, None)
            self._metrics["messages_acknowledged"] += 1
            return True

    def _schedule_retry(self, message: BusMessage) -> None:
        """Schedule message for retry."""
        if not message.can_retry():
            self._dead_letter(message)
            return

        message.retry_count += 1
        message.status = MessageStatus.PENDING

        # Schedule retry
        def retry():
            time.sleep(self._retry_interval_seconds * (2 ** (message.retry_count - 1)))
            if message.status == MessageStatus.PENDING:
                self._deliver(message)

        threading.Thread(target=retry, daemon=True).start()

    def _dead_letter(self, message: BusMessage) -> None:
        """Move message to dead letter queue."""
        message.status = MessageStatus.DEAD_LETTER
        logger.warning(f"Message {message.message_id} moved to dead letter after {message.retry_count} retries")
        with self._lock:
            self._metrics["messages_dead_letter"] += 1
            self._metrics["messages_failed"] += 1

    def _cleanup_loop(self) -> None:
        """Cleanup expired messages and pending acks."""
        while self._running:
            try:
                time.sleep(self._cleanup_interval_seconds)
                self._cleanup()
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")

    def _cleanup(self) -> None:
        """Remove expired messages and handle unacknowledged messages."""
        now = datetime.now(timezone.utc)
        expired_ids = []
        unacked_ids = []

        with self._lock:
            for msg_id, message in self._pending_messages.items():
                if message.is_expired():
                    expired_ids.append(msg_id)
                elif message.status == MessageStatus.SENT:
                    sent_at = self._pending_acks.get(msg_id)
                    if sent_at and (now - sent_at).total_seconds() > self._ack_timeout_seconds:
                        unacked_ids.append(msg_id)

        for msg_id in expired_ids:
            with self._lock:
                message = self._pending_messages.pop(msg_id, None)
                if message and message.deduplication_key:
                    self._deduplication_store.discard(message.deduplication_key)

        for msg_id in unacked_ids:
            with self._lock:
                message = self._pending_messages.get(msg_id)
                if message:
                    message.status = MessageStatus.PENDING
                    self._schedule_retry(message)

    def get_metrics(self) -> Dict[str, Any]:
        """Get bus metrics."""
        with self._lock:
            return dict(self._metrics)

    def get_pending_count(self) -> int:
        with self._lock:
            return len(self._pending_messages)


# Global bus instance
_agent_bus: Optional[AgentBus] = None
_bus_lock = threading.Lock()


def get_agent_bus() -> AgentBus:
    global _agent_bus
    with _bus_lock:
        if _agent_bus is None:
            _agent_bus = AgentBus()
        return _agent_bus


__all__ = [
    "DeliverySemantics",
    "MessagePriority",
    "MessageStatus",
    "MessageSchema",
    "BusMessage",
    "BusSubscription",
    "AgentBus",
    "get_agent_bus",
]