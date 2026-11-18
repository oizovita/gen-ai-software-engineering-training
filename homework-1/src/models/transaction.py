"""Transaction domain model and request schema."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class TransactionCreate(BaseModel):
    """Raw request body for ``POST /transactions``.

    Fields are intentionally loose (``Any``) so that the custom validator can
    produce a single, well-formatted list of errors instead of pydantic's
    default 422 response.
    """

    model_config = ConfigDict(extra="ignore")

    fromAccount: Optional[Any] = None
    toAccount: Optional[Any] = None
    amount: Optional[Any] = None
    currency: Optional[Any] = None
    type: Optional[Any] = None


class Transaction(BaseModel):
    """Stored transaction as returned by the API."""

    id: str
    fromAccount: Optional[str] = None
    toAccount: Optional[str] = None
    amount: float = Field(gt=0)
    currency: str
    type: TransactionType
    timestamp: str
    status: TransactionStatus

    def involves(self, account_id: str) -> bool:
        return account_id in (self.fromAccount, self.toAccount)
