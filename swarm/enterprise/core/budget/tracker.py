"""
Budget Tracker - Budget tracking, allocation, and cost management.
"""

import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Budget Models
# =============================================================================

class BudgetType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    PROJECT = "project"
    CUSTOM = "custom"


class BudgetStatus(str, Enum):
    ACTIVE = "active"
    EXCEEDED = "exceeded"
    WARNING = "warning"
    EXPIRED = "expired"
    CLOSED = "closed"


class AllocationStrategy(str, Enum):
    EQUAL = "equal"
    PROPORTIONAL = "proportional"
    PRIORITY_BASED = "priority_based"
    DEMAND_BASED = "demand_based"
    FIXED = "fixed"


@dataclass
class BudgetAccount:
    """A budget account with limits and tracking."""
    account_id: str = field(default_factory=lambda: f"budget-{uuidv7()}")
    name: str = ""
    description: str = ""
    budget_type: BudgetType = BudgetType.MONTHLY
    
    # Limits
    limit: float = 0.0
    spent: float = 0.0
    reserved: float = 0.0  # Reserved but not yet spent
    
    # Period
    period_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30))
    
    # Currency
    currency: str = "USD"
    
    # Status
    status: BudgetStatus = BudgetStatus.ACTIVE
    
    # Hierarchy
    parent_account_id: Optional[str] = None
    child_account_ids: Set[str] = field(default_factory=set)
    
    # Metadata
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Alerts
    warning_threshold: float = 0.8  # 80%
    critical_threshold: float = 0.95  # 95%
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def available(self) -> float:
        return max(0.0, self.limit - self.spent - self.reserved)
    
    @property
    def utilization(self) -> float:
        if self.limit <= 0:
            return 0.0
        return (self.spent + self.reserved) / self.limit
    
    @property
    def is_warning(self) -> bool:
        return self.utilization >= self.warning_threshold
    
    @property
    def is_critical(self) -> bool:
        return self.utilization >= self.critical_threshold
    
    @property
    def is_exceeded(self) -> bool:
        return self.utilization >= 1.0
    
    def days_remaining(self) -> int:
        delta = self.period_end - datetime.now(timezone.utc)
        return max(0, delta.days)


@dataclass
class BudgetAllocation:
    """An allocation of budget to a consumer."""
    allocation_id: str = field(default_factory=lambda: f"alloc-{uuidv7()}")
    account_id: str = ""
    consumer_id: str = ""  # Could be project_id, team_id, user_id, etc.
    consumer_type: str = "project"  # project, team, user, department
    amount: float = 0.0
    priority: int = 100
    
    # Period
    start_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_date: Optional[datetime] = None
    
    # Status
    status: str = "active"  # active, expired, cancelled
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def is_active(self) -> bool:
        now = datetime.now(timezone.utc)
        if self.status != "active":
            return False
        if self.end_date and datetime.now(timezone.utc) > self.end_date:
            return False
        return True


@dataclass
class BudgetTransaction:
    """A budget transaction (spend, reserve, release, transfer)."""
    transaction_id: str = field(default_factory=lambda: f"txn-{uuidv7()}")
    account_id: str = ""
    transaction_type: str = ""  # spend, reserve, release, transfer_in, transfer_out, adjust
    amount: float = 0.0
    currency: str = "USD"
    
    # Context
    description: str = ""
    reference_id: Optional[str] = None  # e.g., project_id, order_id
    actor_id: str = "system"
    
    # Balance impact
    spent_delta: float = 0.0
    reserved_delta: float = 0.0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Balance after transaction
    balance_after: float = 0.0


# =============================================================================
# Budget Engine
# =============================================================================

class BudgetEngine:
    """Core budget management engine."""
    
    def __init__(self):
        self._accounts: Dict[str, BudgetAccount] = {}
        self._allocations: Dict[str, BudgetAllocation] = {}
        self._transactions: List[BudgetTransaction] = []
        self._lock = threading.RLock()
        
        # Alert callbacks
        self._alert_callbacks: List[Callable[[BudgetAccount, str], None]] = []
    
    def create_account(
        self,
        name: str,
        limit: float,
        budget_type: BudgetType = BudgetType.MONTHLY,
        period_days: int = 30,
        parent_account_id: Optional[str] = None,
        currency: str = "USD",
        description: str = "",
        tags: Optional[Set[str]] = None,
    ) -> BudgetAccount:
        """Create a new budget account."""
        with self._lock:
            now = datetime.now(timezone.utc)
            period_end = datetime.now(timezone.utc) + timedelta(days=period_days)
            
            account = BudgetAccount(
                name=name,
                description=description,
                budget_type=budget_type,
                limit=limit,
                period_start=now,
                period_end=period_end,
                currency=currency,
                parent_account_id=parent_account_id,
                tags=tags or set(),
            )
            
            self._accounts[account.account_id] = account
            
            # Link to parent
            if parent_account_id and parent_account_id in self._accounts:
                self._accounts[parent_account_id].child_account_ids.add(account.account_id)
            
            logger.info(f"Created budget account: {account.account_id} ({name}) with limit {limit} {currency}")
            return account
    
    def get_account(self, account_id: str) -> Optional[BudgetAccount]:
        with self._lock:
            return self._accounts.get(account_id)
    
    def list_accounts(
        self,
        parent_id: Optional[str] = None,
        status: Optional[BudgetStatus] = None,
        budget_type: Optional[BudgetType] = None,
    ) -> List[BudgetAccount]:
        with self._lock:
            accounts = list(self._accounts.values())
            
            if parent_id:
                accounts = [a for a in accounts if a.parent_account_id == parent_id]
            if status:
                accounts = [a for a in accounts if a.status == status]
            if budget_type:
                accounts = [a for a in accounts if a.budget_type == budget_type]
            
            return accounts
    
    def update_account(self, account_id: str, updates: Dict[str, Any]) -> Optional[BudgetAccount]:
        with self._lock:
            account = self._accounts.get(account_id)
            if not account:
                return None
            
            for key, value in updates.items():
                if hasattr(account, key) and key not in ("account_id", "created_at", "created_by"):
                    setattr(account, key, value)
            
            account.updated_at = datetime.now(timezone.utc)
            logger.info(f"Updated budget account: {account_id}")
            return account
    
    def close_account(self, account_id: str) -> bool:
        with self._lock:
            account = self._accounts.get(account_id)
            if not account:
                return False
            
            account.status = BudgetStatus.CLOSED
            account.updated_at = datetime.now(timezone.utc)
            logger.info(f"Closed budget account: {account_id}")
            return True
    
    def allocate(
        self,
        account_id: str,
        consumer_id: str,
        consumer_type: str,
        amount: float,
        priority: int = 100,
        end_date: Optional[datetime] = None,
    ) -> Optional[BudgetAllocation]:
        """Allocate budget from an account to a consumer."""
        with self._lock:
            account = self._accounts.get(account_id)
            if not account:
                return None
            
            # Check if account has available budget
            available = account.available
            if amount > available:
                logger.warning(f"Insufficient budget in {account_id}: requested {amount}, available {available}")
                return None
            
            # Reserve the amount
            account.reserved += amount
            
            allocation = BudgetAllocation(
                account_id=account_id,
                consumer_id=consumer_id,
                consumer_type=consumer_type,
                amount=amount,
                priority=priority,
                end_date=end_date,
            )
            
            self._allocations[allocation.allocation_id] = allocation
            
            # Record transaction
            self._record_transaction(
                account_id=account_id,
                transaction_type="reserve",
                amount=amount,
                description=f"Allocated to {consumer_type}:{consumer_id}",
                reference_id=allocation.allocation_id,
                actor_id="budget_engine",
            )
            
            logger.info(f"Allocated {amount} from {account_id} to {consumer_type}:{consumer_id}")
            return allocation
    
    def spend(
        self,
        account_id: str,
        amount: float,
        description: str = "",
        reference_id: Optional[str] = None,
        actor_id: str = "system",
    ) -> bool:
        """Record a spend against a budget account."""
        with self._lock:
            account = self._accounts.get(account_id)
            if not account:
                return False
            
            # Check if account can afford the spend
            if amount > account.available:
                logger.warning(f"Insufficient budget for spend: {account_id} (available: {account.available})")
                return False
            
            # Update account
            account.spent += amount
            account.reserved = max(0, account.reserved - amount)
            account.updated_at = now_utc()
            
            # Record transaction
            self._record_transaction(
                account_id=account_id,
                transaction_type="spend",
                amount=amount,
                description=description,
                reference_id=reference_id,
                actor_id=actor_id,
            )
            
            # Check for alerts
            self._check_alerts(account)
            
            logger.info(f"Spent {amount} from {account_id}: {description}")
            return True
    
    def release_reservation(self, allocation_id: str) -> bool:
        """Release a budget reservation."""
        with self._lock:
            allocation = self._allocations.get(allocation_id)
            if not allocation:
                return False
            
            account = self._accounts.get(allocation.account_id)
            if not account:
                return False
            
            # Release reservation
            amount = min(allocation.amount, account.reserved)
            account.reserved -= amount
            allocation.status = "cancelled"
            allocation.updated_at = now_utc()
            
            # Record transaction
            self._record_transaction(
                account_id=allocation.account_id,
                transaction_type="release",
                amount=amount,
                description=f"Released reservation for {allocation.consumer_type}:{allocation.consumer_id}",
                reference_id=allocation_id,
                actor_id="budget_engine",
            )
            
            logger.info(f"Released reservation {allocation_id} ({amount})")
            return True
    
    def transfer(
        self,
        from_account_id: str,
        to_account_id: str,
        amount: float,
        description: str = "",
        actor_id: str = "system",
    ) -> bool:
        """Transfer budget between accounts."""
        with self._lock:
            from_account = self._accounts.get(from_account_id)
            to_account = self._accounts.get(to_account_id)
            
            if not from_account or not to_account:
                return False
            
            if amount > from_account.available:
                logger.warning(f"Insufficient budget for transfer from {from_account_id}")
                return False
            
            # Deduct from source
            from_account.spent += amount
            from_account.reserved = max(0, from_account.reserved - amount)
            from_account.updated_at = now_utc()
            
            # Add to destination (as negative spend = credit)
            to_account.spent -= amount  # Negative spend increases available
            to_account.updated_at = now_utc()
            
            # Record transactions
            self._record_transaction(
                account_id=from_account_id,
                transaction_type="transfer_out",
                amount=amount,
                description=f"Transfer to {to_account_id}: {description}",
                actor_id=actor_id,
            )
            
            self._record_transaction(
                account_id=to_account_id,
                transaction_type="transfer_in",
                amount=amount,
                description=f"Transfer from {from_account_id}: {description}",
                actor_id=actor_id,
            )
            
            logger.info(f"Transferred {amount} from {from_account_id} to {to_account_id}")
            return True
    
    def adjust_limit(self, account_id: str, new_limit: float, actor_id: str = "system") -> bool:
        """Adjust the budget limit of an account."""
        with self._lock:
            account = self._accounts.get(account_id)
            if not account:
                return False
            
            old_limit = account.limit
            account.limit = new_limit
            account.updated_at = now_utc()
            
            # Record transaction
            delta = new_limit - old_limit
            self._record_transaction(
                account_id=account_id,
                transaction_type="adjust",
                amount=abs(delta),
                description=f"Limit adjusted from {old_limit} to {new_limit}",
                actor_id=actor_id,
            )
            
            # Check alerts
            self._check_alerts(account)
            
            logger.info(f"Adjusted limit for {account_id}: {old_limit} -> {new_limit}")
            return True
    
    def get_transactions(
        self,
        account_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[BudgetTransaction]:
        with self._lock:
            txns = self._transactions
            
            if account_id:
                txns = [t for t in txns if t.account_id == account_id]
            if start_time:
                txns = [t for t in txns if t.timestamp >= start_time]
            if end_time:
                txns = [t for t in txns if t.timestamp <= end_time]
            
            txns.sort(key=lambda t: t.timestamp, reverse=True)
            return txns[:limit]
    
    def get_allocations(
        self,
        account_id: Optional[str] = None,
        consumer_id: Optional[str] = None,
        active_only: bool = True,
    ) -> List[BudgetAllocation]:
        with self._lock:
            allocations = list(self._allocations.values())
            
            if account_id:
                allocations = [a for a in allocations if a.account_id == account_id]
            if consumer_id:
                allocations = [a for a in allocations if a.consumer_id == consumer_id]
            if active_only:
                allocations = [a for a in allocations if a.is_active()]
            
            return allocations
    
    def get_account_summary(self, account_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            account = self._accounts.get(account_id)
            if not account:
                return None
            
            allocations = self.get_allocations(account_id=account_id)
            recent_txns = self.get_transactions(account_id=account_id, limit=10)
            
            return {
                "account": {
                    "account_id": account.account_id,
                    "name": account.name,
                    "limit": account.limit,
                    "spent": account.spent,
                    "reserved": account.reserved,
                    "available": account.available,
                    "utilization": account.utilization,
                    "status": account.status.value,
                    "currency": account.currency,
                    "period_start": account.period_start.isoformat(),
                    "period_end": account.period_end.isoformat(),
                    "days_remaining": account.days_remaining(),
                    "is_warning": account.is_warning,
                    "is_critical": account.is_critical,
                    "is_exceeded": account.is_exceeded,
                },
                "allocations": [
                    {
                        "allocation_id": a.allocation_id,
                        "consumer_id": a.consumer_id,
                        "consumer_type": a.consumer_type,
                        "amount": a.amount,
                        "status": a.status,
                    }
                    for a in allocations
                ],
                "recent_transactions": [
                    {
                        "transaction_id": t.transaction_id,
                        "type": t.transaction_type,
                        "amount": t.amount,
                        "description": t.description,
                        "timestamp": t.timestamp.isoformat(),
                    }
                    for t in recent_txns
                ],
            }
    
    def _record_transaction(
        self,
        account_id: str,
        transaction_type: str,
        amount: float,
        description: str = "",
        reference_id: Optional[str] = None,
        actor_id: str = "system",
    ) -> BudgetTransaction:
        account = self._accounts[account_id]
        
        txn = BudgetTransaction(
            account_id=account_id,
            transaction_type=transaction_type,
            amount=amount,
            currency=account.currency,
            description=description,
            reference_id=reference_id,
            actor_id=actor_id,
            spent_delta=amount if transaction_type in ("spend", "reserve") else -amount if transaction_type == "release" else 0,
            reserved_delta=amount if transaction_type == "reserve" else -amount if transaction_type == "release" else 0,
            balance_after=account.available,
        )
        
        self._transactions.append(txn)
        return txn
    
    def _check_alerts(self, account: BudgetAccount) -> None:
        """Check and fire budget alerts."""
        if account.is_critical and not account.status == BudgetStatus.CRITICAL:
            account.status = BudgetStatus.CRITICAL
            self._fire_alert(account, "critical")
        elif account.is_warning and account.status == BudgetStatus.ACTIVE:
            account.status = BudgetStatus.WARNING
            self._fire_alert(account, "warning")
        elif account.is_exceeded:
            account.status = BudgetStatus.EXCEEDED
            self._fire_alert(account, "exceeded")
    
    def _fire_alert(self, account: BudgetAccount, alert_type: str) -> None:
        for callback in self._alert_callbacks:
            try:
                callback(account, alert_type)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    def add_alert_callback(self, callback: Callable[[BudgetAccount, str], None]) -> None:
        self._alert_callbacks.append(callback)
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            accounts = list(self._accounts.values())
            total_limit = sum(a.limit for a in accounts)
            total_spent = sum(a.spent for a in accounts)
            total_reserved = sum(a.reserved for a in accounts)
            
            by_status = defaultdict(int)
            by_type = defaultdict(int)
            
            for a in accounts:
                by_status[a.status.value] += 1
                by_type[a.budget_type.value] += 1
            
            return {
                "total_accounts": len(accounts),
                "total_limit": total_limit,
                "total_spent": total_spent,
                "total_reserved": total_reserved,
                "total_available": total_limit - total_spent - total_reserved,
                "overall_utilization": (total_spent + total_reserved) / max(total_limit, 1),
                "by_status": dict(by_status),
                "by_type": dict(by_type),
                "total_transactions": len(self._transactions),
                "total_allocations": len(self._allocations),
            }


# =============================================================================
# Budget Planner
# =============================================================================

class BudgetPlanner:
    """Helps plan and optimize budget allocations."""
    
    def __init__(self, engine: BudgetEngine):
        self.engine = engine
    
    def plan_allocation(
        self,
        account_id: str,
        demands: List[Dict[str, Any]],  # [{"consumer_id": "", "consumer_type": "", "amount": "", "priority": int}]
        strategy: AllocationStrategy = AllocationStrategy.PROPORTIONAL,
    ) -> List[BudgetAllocation]:
        """Plan allocations based on strategy."""
        account = self.engine.get_account(account_id)
        if not account:
            return []
        
        available = account.available
        if available <= 0:
            return []
        
        # Sort demands by priority
        demands.sort(key=lambda d: d.get("priority", 100))
        
        allocations = []
        
        if strategy == AllocationStrategy.EQUAL:
            # Equal distribution
            per_demand = available / len(demands) if demands else 0
            for demand in demands:
                amount = min(demand["amount"], per_demand)
                alloc = self.engine.allocate(
                    account_id=account_id,
                    consumer_id=demand["consumer_id"],
                    consumer_type=demand["consumer_type"],
                    amount=amount,
                    priority=demand.get("priority", 100),
                )
                if alloc:
                    allocations.append(alloc)
        
        elif strategy == AllocationStrategy.PROPORTIONAL:
            # Proportional to requested amounts
            total_requested = sum(d["amount"] for d in demands)
            for demand in demands:
                proportion = demand["amount"] / total_requested if total_requested > 0 else 0
                amount = available * proportion
                amount = min(amount, demand["amount"])
                alloc = self.engine.allocate(
                    account_id=account_id,
                    consumer_id=demand["consumer_id"],
                    consumer_type=demand["consumer_type"],
                    amount=amount,
                    priority=demand.get("priority", 100),
                )
                if alloc:
                    allocations.append(alloc)
        
        elif strategy == AllocationStrategy.PRIORITY_BASED:
            # Higher priority gets full amount first
            for demand in demands:
                if available <= 0:
                    break
                amount = min(demand["amount"], available)
                alloc = self.engine.allocate(
                    account_id=account_id,
                    consumer_id=demand["consumer_id"],
                    consumer_type=demand["consumer_type"],
                    amount=amount,
                    priority=demand.get("priority", 100),
                )
                if alloc:
                    allocations.append(alloc)
                    available -= alloc.amount
        
        return allocations


# =============================================================================
# Factory
# =============================================================================

def create_budget_engine() -> BudgetEngine:
    return BudgetEngine()


def create_budget_planner(engine: BudgetEngine) -> BudgetPlanner:
    return BudgetPlanner(engine)
