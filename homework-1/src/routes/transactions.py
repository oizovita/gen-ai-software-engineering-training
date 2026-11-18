"""/transactions endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse

from src.models.transaction import Transaction, TransactionStatus, TransactionType
from src.storage.memory import store
from src.utils.helpers import generate_id, parse_filter_date, transactions_to_csv, utc_now_iso
from src.validators.transaction_validator import (
    ACCOUNT_PATTERN,
    ValidationError,
    validate_transaction_payload,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _resolve_status(data: Dict[str, Any]) -> TransactionStatus:
    """Withdrawals/transfers that exceed the source balance are recorded as failed."""
    if data["type"] in (TransactionType.WITHDRAWAL, TransactionType.TRANSFER):
        if store.balance(data["fromAccount"]) < data["amount"]:
            return TransactionStatus.FAILED
    return TransactionStatus.COMPLETED


async def _read_json_body(request: Request) -> Dict[str, Any]:
    try:
        body = await request.json()
    except ValueError:
        raise ValidationError([{"field": "body", "message": "Request body must be valid JSON"}])
    if not isinstance(body, dict):
        raise ValidationError([{"field": "body", "message": "Request body must be a JSON object"}])
    return body


def _parse_filters(
    account_id: Optional[str],
    tx_type: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
) -> Dict[str, Any]:
    """Validate query-string filters; collect every problem into one 400 response."""
    details: List[Dict[str, str]] = []
    parsed: Dict[str, Any] = {}

    if account_id is not None:
        if not ACCOUNT_PATTERN.match(account_id):
            details.append(
                {"field": "accountId", "message": "Account number must match format ACC-XXXXX"}
            )
        parsed["account_id"] = account_id

    if tx_type is not None:
        try:
            parsed["tx_type"] = TransactionType(tx_type)
        except ValueError:
            details.append(
                {"field": "type", "message": "Type must be one of: deposit, withdrawal, transfer"}
            )

    for field, raw, end_of_range in (("from", date_from, False), ("to", date_to, True)):
        if raw is None:
            continue
        try:
            parsed["date_from" if field == "from" else "date_to"] = parse_filter_date(
                raw, end_of_range=end_of_range
            )
        except ValueError:
            details.append(
                {"field": field, "message": "Date must be YYYY-MM-DD or an ISO 8601 datetime"}
            )

    start: Optional[datetime] = parsed.get("date_from")
    end: Optional[datetime] = parsed.get("date_to")
    if start and end and start > end:
        details.append({"field": "to", "message": "'to' must not be earlier than 'from'"})

    if details:
        raise ValidationError(details)
    return parsed


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Transaction)
async def create_transaction(request: Request) -> Transaction:
    body = await _read_json_body(request)
    data = validate_transaction_payload(body)
    transaction = Transaction(
        id=generate_id(),
        timestamp=utc_now_iso(),
        status=_resolve_status(data),
        **data,
    )
    return store.add(transaction)


@router.get("", response_model=List[Transaction])
async def list_transactions(
    accountId: Optional[str] = Query(None, description="Account id (matches from or to)"),
    type: Optional[str] = Query(None, description="deposit | withdrawal | transfer"),
    from_: Optional[str] = Query(None, alias="from", description="YYYY-MM-DD or ISO datetime"),
    to: Optional[str] = Query(None, description="YYYY-MM-DD (inclusive) or ISO datetime"),
) -> List[Transaction]:
    filters = _parse_filters(accountId, type, from_, to)
    return store.list(**filters)


@router.get(
    "/export",
    response_class=PlainTextResponse,
    responses={200: {"content": {"text/csv": {}}, "description": "CSV file download"}},
)
async def export_transactions(
    format: str = Query("csv", description="Export format (only csv is supported)"),
    accountId: Optional[str] = Query(None, description="Account id (matches from or to)"),
    type: Optional[str] = Query(None, description="deposit | withdrawal | transfer"),
    from_: Optional[str] = Query(None, alias="from", description="YYYY-MM-DD or ISO datetime"),
    to: Optional[str] = Query(None, description="YYYY-MM-DD (inclusive) or ISO datetime"),
):
    """Export transactions as CSV. Accepts the same filters as the list endpoint.

    Declared before ``/{transaction_id}`` so that "export" is not treated as an id.
    """
    if format.lower() != "csv":
        raise ValidationError([{"field": "format", "message": "Only 'csv' format is supported"}])
    filters = _parse_filters(accountId, type, from_, to)
    csv_text = transactions_to_csv(store.list(**filters))
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="transactions.csv"'},
    )


@router.get("/{transaction_id}", response_model=Transaction)
async def get_transaction(transaction_id: str):
    transaction = store.get(transaction_id)
    if transaction is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND, content={"error": "Transaction not found"}
        )
    return transaction
