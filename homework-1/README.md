# 🏦 Homework 1: Banking Transactions API

> **Student Name**: Oles Izovita
> **Date Submitted**: 2026-11-18
> **AI Tools Used**: Claude Code (Claude Fable 5.1)

---

## 📋 Project Overview

A minimal REST API for banking transactions built with **Python 3.13 + FastAPI**.
Transactions live in an in-memory store (no database). The API creates
deposits, withdrawals and transfers, validates every request, computes account
balances, filters transaction history and exports it as CSV.

The whole implementation was produced in a planned, step-by-step session with
Claude Code: plan → Task 1 → Task 2 → Task 3 → Task 4 → docs/tests, with the
API exercised via `curl` after every step (see `docs/screenshots/`).

## ✨ Features Implemented

| Task | Status | What was built |
|------|--------|----------------|
| **Task 1 – Core API** | ✅ | `POST /transactions`, `GET /transactions`, `GET /transactions/{id}`, `GET /accounts/{accountId}/balance`; in-memory store; 200/201/400/404 codes; JSON error bodies |
| **Task 2 – Validation** | ✅ | Positive amount with ≤ 2 decimals, `ACC-XXXXX` account format, ISO 4217 currency codes, allowed `type` values, type-dependent required accounts. All problems are reported together in the `{"error": "Validation failed", "details": [...]}` format |
| **Task 3 – History filters** | ✅ | `?accountId=`, `?type=`, `?from=`/`?to=` (date or ISO datetime), any combination; invalid filters → 400 |
| **Task 4 – Option C: CSV export** | ✅ | `GET /transactions/export?format=csv` → `text/csv` download, supports the same filters as the list endpoint |
| Extras | ✅ | Swagger UI at `/docs`, `/health`, optional seeding from `demo/sample-data.json`, 26 pytest tests |

## 🔌 API Reference

| Method | Endpoint | Description | Codes |
|--------|----------|-------------|-------|
| `POST` | `/transactions` | Create a transaction | 201, 400 |
| `GET` | `/transactions` | List transactions (filters: `accountId`, `type`, `from`, `to`) | 200, 400 |
| `GET` | `/transactions/export?format=csv` | Export transactions as CSV (same filters) | 200, 400 |
| `GET` | `/transactions/{id}` | Get one transaction | 200, 404 |
| `GET` | `/accounts/{accountId}/balance` | Current balance of an account | 200, 400, 404 |
| `GET` | `/health` | Liveness check | 200 |
| `GET` | `/docs` | Interactive Swagger UI | 200 |

**Transaction model**

```json
{
  "id": "4e21686f-9790-4ce9-ac80-6fc079eba488",
  "fromAccount": "ACC-12345",
  "toAccount": "ACC-67890",
  "amount": 100.5,
  "currency": "USD",
  "type": "transfer",
  "timestamp": "2026-11-18T20:07:52.426Z",
  "status": "completed"
}
```

**Validation error format**

```json
{
  "error": "Validation failed",
  "details": [
    {"field": "amount", "message": "Amount must be a positive number"},
    {"field": "currency", "message": "Invalid currency code"}
  ]
}
```

## 🏗️ Architecture & Design Decisions

```
src/
├── app.py                 # create_app(): routers, error handlers, optional seeding
├── models/transaction.py  # Enums + pydantic models (TransactionCreate, Transaction)
├── validators/            # Business validation → assignment's error format
├── storage/memory.py      # MemoryStore: list (ordered) + dict (O(1) by id), filters, balance
├── routes/transactions.py # /transactions endpoints (export is declared before /{id})
├── routes/accounts.py     # /accounts/{id}/balance
└── utils/helpers.py       # uuid, UTC timestamps, date parsing, CSV serializer
```

- **FastAPI + uvicorn** — small, typed, ships Swagger UI for free. Port **3000**
  to match the `curl` examples in the assignment.
- **Custom validation layer instead of relying on pydantic alone.** The
  assignment prescribes an exact error shape, so request bodies are parsed as
  raw JSON and run through `validators/transaction_validator.py`, which collects
  *every* problem (not just the first). FastAPI's own 422 errors are also
  remapped to 400 in the same shape, so clients see one format.
- **Type-dependent account rules.** `deposit` needs only `toAccount`,
  `withdrawal` only `fromAccount`, `transfer` both (and they must differ).
  Fields that are present are always format-checked (`^ACC-[A-Za-z0-9]{5}$`).
- **Balance = Σ incoming − Σ outgoing of `completed` transactions.** A
  withdrawal/transfer that exceeds the source balance is still recorded
  (HTTP 201) but with `status: "failed"`, so history is kept and the balance is
  never negative. `pending`/`failed` rows do not affect balances.
- **ISO 4217 as a fixed set** (50 common codes) to stay dependency-free;
  currency codes are case-insensitive and normalised to upper-case.
- **Date filters** accept `YYYY-MM-DD` or a full ISO datetime; a plain date in
  `to` covers the whole day (inclusive). `from > to` is rejected.
- **CSV export route is registered before `/{id}`**, otherwise FastAPI would
  treat `export` as a transaction id.
- **In-memory store as a module singleton** (`storage.memory.store`). Simple for
  the assignment; the `MemoryStore` class could be swapped for a DB-backed
  implementation behind the same interface.

## 🧪 Testing

```bash
.venv/bin/pytest          # 26 tests: endpoints, validation, filters, failed status, CSV
bash demo/sample-requests.sh   # curl walkthrough against a running server
```

## 🤖 AI-Assisted Workflow

1. **Planning prompt** — described the assignment and constraints; Claude Code
   proposed a file layout, key decisions (status=failed on insufficient funds,
   custom validation layer, CSV option) and a step-by-step plan with checkpoints.
2. **Task 1** — generated the skeleton (models, store, routes, app factory),
   created the venv, started uvicorn and smoke-tested with `curl`.
3. **Task 2** — rewrote the validator with all rules, re-tested invalid payloads.
4. **Task 3** — added query filters, sample data and seed support.
5. **Task 4C** — CSV serializer + export endpoint.
6. **Deliverables** — pytest suite, `demo/` scripts, this README, HOWTORUN.

What worked well: asking for a plan first, then implementing one task at a time
with a `curl` check after each. Things I reviewed/adjusted by hand: CSV amount
formatting (`1500.0` → `1500.00`) and the decision that insufficient funds
should produce a `failed` transaction rather than an HTTP error.

## 📸 Screenshots

All screenshots are in `docs/screenshots/`, in chronological order of the session.

**AI tool interactions (prompts, planning, generated code)**

| File | Shows |
|------|-------|
| `screenshot_01_prompt.png` | Initial prompt to Claude Code describing the assignment |
| `screenshot_02_plan_framework_choice.png` | Plan mode: choosing the web framework (FastAPI + uvicorn) |
| `screenshot_03_plan_task4_option_choice.png` | Plan mode: choosing the Task 4 feature (Option C, CSV export) |
| `screenshot_04_plan_balance_decision.png` | Plan mode: how to treat insufficient funds (`status: failed`) |
| `screenshot_05_plan_file_structure.png` | Generated plan, part 1: context and file structure |
| `screenshot_06_plan_decisions_and_steps.png` | Generated plan, part 2: key decisions, step order, verification |
| `screenshot_07_task1_ai_generated_code.png` | Task 1: generated validator code, diff of created files, AI summary |
| `screenshot_13_task2_ai_summary.png` | Task 2: AI summary of the validation rules implemented |
| `screenshot_16_task3_ai_summary.png` | Task 3: AI summary of filters and seed data |
| `screenshot_21_task4_ai_summary.png` | Task 4C: AI summary of the CSV export endpoint |
| `screenshot_23_deliverables_ai_summary.png` | Final step: AI summary of tests, demo scripts and docs |

**API running**

| File | Shows |
|------|-------|
| `screenshot_08_api_running.png` | uvicorn serving the API on `http://0.0.0.0:3000` |
| `screenshot_24_tests_passed.png` | `pytest -v`: 26 tests passed |
| `screenshot_25_swagger_docs.png` | Swagger UI at `/docs` with all endpoints |

**Sample requests / responses (curl)**

| File | Shows |
|------|-------|
| `screenshot_09_task1_post_transactions.png` | `POST /transactions`: deposit and transfer → 201 |
| `screenshot_10_task1_get_transactions.png` | `GET /transactions`: full list |
| `screenshot_11_task1_get_transaction_by_id.png` | `GET /transactions/{id}` |
| `screenshot_12_task1_get_balance.png` | `GET /accounts/ACC-12345/balance` |
| `screenshot_14_task2_validation_errors.png` | 400 with four `details` (amount, currency, fromAccount, toAccount) |
| `screenshot_15_task2_invalid_json_body.png` | 400 for a malformed JSON body |
| `screenshot_17_task3_filter_by_account.png` | `?accountId=ACC-12345` |
| `screenshot_18_task3_filter_by_type.png` | `?type=transfer` |
| `screenshot_19_task3_filter_by_date_range.png` | `?from=2024-01-01&to=2024-01-31` |
| `screenshot_20_task3_combined_filters.png` | All filters combined → exactly one transaction |
| `screenshot_22_task4_csv_export.png` | `GET /transactions/export?format=csv` with headers and CSV body |

<div align="center">

*This project was completed as part of the AI-Assisted Development course.*

</div>
