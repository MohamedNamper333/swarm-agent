"""
Budget Ledger — atomic budget reservation with race-condition protection.

F-003: Budget Race Condition fix.
Ensures atomic check-and-reserve for budget operations.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
from decimal import Decimal
from enum import Enum
import threading
import time
import uuid
from datetime import datetime, timezone


class BudgetType(str, Enum):
    DAILY = "daily"
    MONTHLY = "monthly"
    PER_REQUEST = "per_request"
    PER_TENANT = "per_tenant"


@dataclass(frozen=True)
class BudgetAccount:
    """Budget account with atomic reservation tracking."""
    account_id: str
    tenant_id: str
    budget_type: BudgetType
    limit: Decimal
    available: Decimal
    reserved: Decimal
    consumed: Decimal
    released: Decimal
    period_start: datetime
    period_end: datetime
    version: int  # For optimistic locking


@dataclass
class Reservation:
    """A budget reservation."""
    reservation_id: str
    account_id: str
    amount: Decimal
    created_at: datetime
    expires_at: Optional[datetime]
    status: str  # "active", "consumed", "released", "expired"
    metadata: Dict = field(default_factory=dict)


class BudgetLedger:
    """Thread-safe budget ledger with atomic reservations."""

    def __init__(self):
        self._accounts: Dict[str, BudgetAccount] = {}
        self._reservations: Dict[str, Reservation] = {}
        self._lock = threading.RLock()

    def create_account(
        self,
        account_id: str,
        tenant_id: str,
        budget_type: BudgetType,
        limit: Decimal,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> BudgetAccount:
        """Create a new budget account."""
        now = datetime.now(timezone.utc)
        with self._lock:
            if account_id in self._accounts:
                raise ValueError(f"Account {account_id} already exists")

            if period_start is None:
                period_start = now
            if period_end is None:
                # Default to end of day for daily, end of month for monthly
                if budget_type == BudgetType.DAILY:
                    period_end = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)
                elif budget_type == BudgetType.MONTHLY:
                    # Last day of month
                    if now.month == 12:
                        period_end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
                    else:
                        period_end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
                else:
                    period_end = now

            account = BudgetAccount(
                account_id=account_id,
                tenant_id=tenant_id,
                budget_type=budget_type,
                limit=limit,
                available=limit,
                reserved=Decimal("0"),
                consumed=Decimal("0"),
                released=Decimal("0"),
                period_start=period_start,
                period_end=period_end,
                version=0,
            )
            self._accounts[account_id] = account
            return account

    def get_account(self, account_id: str) -> Optional[BudgetAccount]:
        """Get account by ID."""
        with self._lock:
            return self._accounts.get(account_id)

    def reserve(
        self,
        account_id: str,
        amount: Decimal,
        reservation_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict] = None,
    ) -> Reservation:
        """Atomically reserve budget. Raises if insufficient funds."""
        if amount <= 0:
            raise ValueError("Reservation amount must be positive")

        with self._lock:
            account = self._accounts.get(account_id)
            if not account:
                raise KeyError(f"Account {account_id} not found")

            # Check available (limit - reserved - consumed)
            available = account.limit - account.reserved - account.consumed
            if available < amount:
                raise ValueError(
                    f"Insufficient budget: available={available}, requested={amount}, "
                    f"limit={account.limit}, reserved={account.reserved}, consumed={account.consumed}"
                )

            # Atomic reservation
            new_reserved = account.reserved + amount
            new_available = account.available - amount
            new_version = account.version + 1

            # Create new account with updated values (immutable pattern)
            updated_account = BudgetAccount(
                account_id=account.account_id,
                tenant_id=account.tenant_id,
                budget_type=account.budget_type,
                limit=account.limit,
                available=new_available,
                reserved=new_reserved,
                consumed=account.consumed,
                released=account.released,
                period_start=account.period_start,
                period_end=account.period_end,
                version=new_version,
            )
            self._accounts[account_id] = updated_account

            # Create reservation
            res_id = reservation_id or str(uuid.uuid4())
            reservation = Reservation(
                reservation_id=res_id,
                account_id=account_id,
                amount=amount,
                created_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                status="active",
                metadata=metadata or {},
            )
            self._reservations[res_id] = reservation
            return reservation

    def consume(self, reservation_id: str, actual_amount: Optional[Decimal] = None) -> Decimal:
        """Convert reservation to consumption. Returns actual amount consumed."""
        with self._lock:
            reservation = self._reservations.get(reservation_id)
            if not reservation:
                raise KeyError(f"Reservation {reservation_id} not found")
            if reservation.status != "active":
                raise ValueError(f"Reservation {reservation_id} not active (status={reservation.status})")

            account = self._accounts.get(reservation.account_id)
            if not account:
                raise KeyError(f"Account {reservation.account_id} not found")

            consume_amount = actual_amount if actual_amount is not None else reservation.amount
            if consume_amount <= 0:
                raise ValueError("Consumption amount must be positive")

            # Update account: reserved -> consumed
            new_reserved = account.reserved - reservation.amount
            new_consumed = account.consumed + consume_amount
            new_available = account.available  # available doesn't change on consume
            new_version = account.version + 1

            updated_account = BudgetAccount(
                account_id=account.account_id,
                tenant_id=account.tenant_id,
                budget_type=account.budget_type,
                limit=account.limit,
                available=new_available,
                reserved=new_reserved,
                consumed=new_consumed,
                released=account.released,
                period_start=account.period_start,
                period_end=account.period_end,
                version=new_version,
            )
            self._accounts[reservation.account_id] = updated_account

            # Update reservation
            reservation.status = "consumed"
            return consume_amount

    def release(self, reservation_id: str) -> Decimal:
        """Release an active reservation back to available."""
        with self._lock:
            reservation = self._reservations.get(reservation_id)
            if not reservation:
                raise KeyError(f"Reservation {reservation_id} not found")
            if reservation.status != "active":
                raise ValueError(f"Reservation {reservation_id} not active (status={reservation.status})")

            account = self._accounts.get(reservation.account_id)
            if not account:
                raise KeyError(f"Account {reservation.account_id} not found")

            # Update account: reserved -> released, available increases
            new_reserved = account.reserved - reservation.amount
            new_released = account.released + reservation.amount
            new_available = account.available + reservation.amount
            new_version = account.version + 1

            updated_account = BudgetAccount(
                account_id=account.account_id,
                tenant_id=account.tenant_id,
                budget_type=account.budget_type,
                limit=account.limit,
                available=new_available,
                reserved=new_reserved,
                consumed=account.consumed,
                released=new_released,
                period_start=account.period_start,
                period_end=account.period_end,
                version=new_version,
            )
            self._accounts[reservation.account_id] = updated_account

            # Update reservation
            reservation.status = "released"
            return reservation.amount

    def get_reservation(self, reservation_id: str) -> Optional[Reservation]:
        """Get reservation by ID."""
        with self._lock:
            return self._reservations.get(reservation_id)

    def get_account_status(self, account_id: str) -> Optional[Dict]:
        """Get current account status."""
        with self._lock:
            account = self._accounts.get(account_id)
            if not account:
                return None
            return {
                "account_id": account.account_id,
                "tenant_id": account.tenant_id,
                "budget_type": account.budget_type.value,
                "limit": str(account.limit),
                "available": str(account.available),
                "reserved": str(account.reserved),
                "consumed": str(account.consumed),
                "released": str(account.released),
                "version": account.version,
                "period_start": account.period_start.isoformat(),
                "period_end": account.period_end.isoformat(),
                "invariant_ok": (account.reserved + account.consumed) <= account.limit,
            }

    def cleanup_expired(self) -> int:
        """Release expired reservations. Returns count released."""
        now = datetime.now(timezone.utc)
        released = 0
        with self._lock:
            for res in list(self._reservations.values()):
                if res.status == "active" and res.expires_at and res.expires_at <= now:
                    self.release(res.reservation_id)
                    released += 1
        return released


# Global ledger instance
_budget_ledger: Optional[BudgetLedger] = None
_ledger_lock = threading.Lock()


def get_budget_ledger() -> BudgetLedger:
    global _budget_ledger
    with _ledger_lock:
        if _budget_ledger is None:
            _budget_ledger = BudgetLedger()
        return _budget_ledger


__all__ = [
    "BudgetType",
    "BudgetAccount",
    "Reservation",
    "BudgetLedger",
    "get_budget_ledger",
]