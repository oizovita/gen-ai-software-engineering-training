"""Request validation for transactions.

Produces the error format required by the assignment::

    {"error": "Validation failed", "details": [{"field": ..., "message": ...}]}

Every rule is checked and all problems are reported together, so a client can
fix a request in one round-trip.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from src.models.transaction import TransactionType

ValidationDetail = Dict[str, str]

# Account numbers: "ACC-" followed by exactly five alphanumeric characters.
ACCOUNT_PATTERN = re.compile(r"^ACC-[A-Za-z0-9]{5}$")

# ISO 4217 codes accepted by the API. A fixed set keeps the service dependency-free.
ISO_4217_CURRENCIES = frozenset(
    {
        "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "UAH", "PLN", "CZK",
        "HUF", "RON", "BGN", "SEK", "NOK", "DKK", "ISK", "CNY", "HKD", "SGD", "INR",
        "KRW", "TWD", "THB", "MYR", "IDR", "PHP", "VND", "ILS", "TRY", "AED", "SAR",
        "QAR", "KWD", "EGP", "ZAR", "NGN", "KES", "MAD", "BRL", "MXN", "ARS", "CLP",
        "COP", "PEN", "GEL", "KZT", "MDL", "RSD",
    }
)


class ValidationError(Exception):
    def __init__(self, details: List[ValidationDetail]) -> None:
        super().__init__("Validation failed")
        self.details = details

    def to_response(self) -> Dict[str, Any]:
        return {"error": "Validation failed", "details": self.details}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _has_at_most_two_decimals(value: float) -> bool:
    try:
        return Decimal(str(value)).as_tuple().exponent >= -2
    except InvalidOperation:
        return False


def _validate_amount(amount: Any, details: List[ValidationDetail]) -> None:
    if amount is None:
        details.append({"field": "amount", "message": "Amount is required"})
        return
    if not _is_number(amount) or amount <= 0:
        details.append({"field": "amount", "message": "Amount must be a positive number"})
        return
    if not _has_at_most_two_decimals(amount):
        details.append(
            {"field": "amount", "message": "Amount must have at most 2 decimal places"}
        )


def _validate_currency(currency: Any, details: List[ValidationDetail]) -> None:
    if currency is None or currency == "":
        details.append({"field": "currency", "message": "Currency is required"})
        return
    if not isinstance(currency, str) or currency.upper() not in ISO_4217_CURRENCIES:
        details.append({"field": "currency", "message": "Invalid currency code"})


def _validate_type(tx_type: Any, details: List[ValidationDetail]) -> Optional[TransactionType]:
    if tx_type is None:
        details.append({"field": "type", "message": "Type is required"})
        return None
    try:
        return TransactionType(tx_type)
    except ValueError:
        details.append(
            {"field": "type", "message": "Type must be one of: deposit, withdrawal, transfer"}
        )
        return None


def _validate_account_format(field: str, value: Any, details: List[ValidationDetail]) -> bool:
    """Return True when the value is a well-formed account id."""
    if not isinstance(value, str) or not ACCOUNT_PATTERN.match(value):
        details.append(
            {"field": field, "message": "Account number must match format ACC-XXXXX"}
        )
        return False
    return True


def _validate_accounts(
    tx_type: Optional[TransactionType],
    from_account: Any,
    to_account: Any,
    details: List[ValidationDetail],
) -> None:
    """Which accounts are required depends on the transaction type."""
    needs_from = tx_type in (TransactionType.WITHDRAWAL, TransactionType.TRANSFER)
    needs_to = tx_type in (TransactionType.DEPOSIT, TransactionType.TRANSFER)

    if needs_from and from_account in (None, ""):
        details.append(
            {"field": "fromAccount", "message": f"fromAccount is required for {tx_type.value}"}
        )
    elif from_account not in (None, ""):
        _validate_account_format("fromAccount", from_account, details)

    if needs_to and to_account in (None, ""):
        details.append(
            {"field": "toAccount", "message": f"toAccount is required for {tx_type.value}"}
        )
    elif to_account not in (None, ""):
        _validate_account_format("toAccount", to_account, details)

    if tx_type is TransactionType.TRANSFER and from_account and from_account == to_account:
        details.append({"field": "toAccount", "message": "toAccount must differ from fromAccount"})


def validate_account_id(account_id: str) -> None:
    """Validate a path parameter such as /accounts/{accountId}/balance."""
    details: List[ValidationDetail] = []
    _validate_account_format("accountId", account_id, details)
    if details:
        raise ValidationError(details)


def validate_transaction_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a raw request body and return a normalized dict.

    Raises ``ValidationError`` with every problem found (not just the first).
    """
    details: List[ValidationDetail] = []

    _validate_amount(payload.get("amount"), details)
    _validate_currency(payload.get("currency"), details)
    tx_type = _validate_type(payload.get("type"), details)
    _validate_accounts(tx_type, payload.get("fromAccount"), payload.get("toAccount"), details)

    if details:
        raise ValidationError(details)

    return {
        "fromAccount": payload.get("fromAccount") or None,
        "toAccount": payload.get("toAccount") or None,
        "amount": float(payload["amount"]),
        "currency": str(payload["currency"]).upper(),
        "type": tx_type,
    }
