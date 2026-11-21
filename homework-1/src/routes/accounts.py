"""/accounts endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.storage.memory import store
from src.validators.transaction_validator import validate_account_id

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/{account_id}/balance")
async def get_balance(account_id: str):
    validate_account_id(account_id)
    if not store.has_account(account_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND, content={"error": "Account not found"}
        )
    return {"accountId": account_id, "balance": store.balance(account_id), "currency": "USD"}
