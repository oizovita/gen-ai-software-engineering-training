"""FastAPI application factory and entry point.

Run with:  uvicorn src.app:app --host 0.0.0.0 --port 3000
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.models.transaction import Transaction, TransactionStatus, TransactionType
from src.routes import accounts, transactions
from src.storage.memory import store
from src.utils.helpers import generate_id, utc_now_iso
from src.validators.transaction_validator import ValidationError


def _seed_from_file(path: str) -> int:
    """Load sample transactions from a JSON array (used by demo/run.sh)."""
    with open(path, encoding="utf-8") as fh:
        items = json.load(fh)
    for raw in items:
        transaction = Transaction(
            id=raw.get("id") or generate_id(),
            fromAccount=raw.get("fromAccount"),
            toAccount=raw.get("toAccount"),
            amount=float(raw["amount"]),
            currency=raw["currency"],
            type=TransactionType(raw["type"]),
            timestamp=raw.get("timestamp") or utc_now_iso(),
            status=TransactionStatus(raw.get("status", "completed")),
        )
        store.add(transaction)
    return len(items)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Banking Transactions API",
        version="1.0.0",
        description="Minimal in-memory REST API for banking transactions (Homework 1).",
    )

    app.include_router(transactions.router)
    app.include_router(accounts.router)

    @app.exception_handler(ValidationError)
    async def handle_validation_error(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=exc.to_response())

    @app.exception_handler(RequestValidationError)
    async def handle_fastapi_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Map FastAPI's default 422 into the assignment's 400 error format.
        details = [
            {"field": ".".join(str(p) for p in err.get("loc", []) if p not in ("body", "query")) or "body",
             "message": err.get("msg", "Invalid value")}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Validation failed", "details": details},
        )

    @app.get("/", include_in_schema=False)
    async def root() -> Dict[str, Any]:
        return {"name": app.title, "version": app.version, "docs": "/docs"}

    @app.get("/health", tags=["meta"])
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    seed_file = os.getenv("SEED_FILE")
    if seed_file and os.path.exists(seed_file):
        _seed_from_file(seed_file)

    return app


app = create_app()
