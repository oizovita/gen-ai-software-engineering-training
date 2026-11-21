"""In-memory transaction store.

A plain list keeps insertion order (useful for listing/export) and a dict
gives O(1) lookup by id. Nothing is persisted; restarting the server clears it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from src.models.transaction import Transaction, TransactionStatus, TransactionType
from src.utils.helpers import parse_timestamp


class MemoryStore:
    def __init__(self) -> None:
        self._items: List[Transaction] = []
        self._by_id: Dict[str, Transaction] = {}

    # --- write -----------------------------------------------------------
    def add(self, transaction: Transaction) -> Transaction:
        self._items.append(transaction)
        self._by_id[transaction.id] = transaction
        return transaction

    def clear(self) -> None:
        self._items.clear()
        self._by_id.clear()

    # --- read ------------------------------------------------------------
    def get(self, transaction_id: str) -> Optional[Transaction]:
        return self._by_id.get(transaction_id)

    def list(
        self,
        *,
        account_id: Optional[str] = None,
        tx_type: Optional[TransactionType] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Transaction]:
        result = self._items
        if account_id is not None:
            result = [t for t in result if t.involves(account_id)]
        if tx_type is not None:
            result = [t for t in result if t.type == tx_type]
        if date_from is not None:
            result = [t for t in result if parse_timestamp(t.timestamp) >= date_from]
        if date_to is not None:
            result = [t for t in result if parse_timestamp(t.timestamp) <= date_to]
        return list(result)

    def balance(self, account_id: str) -> float:
        """Sum of completed incoming minus completed outgoing amounts."""
        total = 0.0
        for t in self._items:
            if t.status != TransactionStatus.COMPLETED:
                continue
            if t.toAccount == account_id:
                total += t.amount
            if t.fromAccount == account_id:
                total -= t.amount
        return round(total, 2)

    def has_account(self, account_id: str) -> bool:
        return any(t.involves(account_id) for t in self._items)


store = MemoryStore()
