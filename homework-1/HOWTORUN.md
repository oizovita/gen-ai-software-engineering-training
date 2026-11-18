# ▶️ How to Run the application

## Prerequisites

- Python **3.11+** (tested with 3.13)
- `curl` (for the sample requests) — optional

All commands below are run from the `homework-1/` directory.

## 1. Quick start (recommended)

```bash
./demo/run.sh
```

The script creates `.venv/` (if missing), installs `requirements.txt` and starts
the API on **http://localhost:3000**. Swagger UI: http://localhost:3000/docs

Useful variants:

```bash
SEED=1 ./demo/run.sh      # pre-load demo/sample-data.json (8 transactions, Jan–Mar 2024)
PORT=8080 ./demo/run.sh   # run on another port
```

Stop with `Ctrl+C`.

## 2. Manual setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn src.app:app --host 0.0.0.0 --port 3000 --reload
```

Optional seeding: `SEED_FILE=demo/sample-data.json .venv/bin/uvicorn src.app:app --port 3000`

## 3. Try the API

**curl walkthrough** (covers all four tasks, prints HTTP codes):

```bash
bash demo/sample-requests.sh
```

**VS Code REST Client**: open `demo/sample-requests.http` and click *Send Request*.

**Single requests:**

```bash
# Create a transaction
curl -X POST http://localhost:3000/transactions \
  -H "Content-Type: application/json" \
  -d '{"fromAccount":"ACC-12345","toAccount":"ACC-67890","amount":100.50,"currency":"USD","type":"transfer"}'

# List / filter
curl "http://localhost:3000/transactions"
curl "http://localhost:3000/transactions?accountId=ACC-12345&type=transfer&from=2024-01-01&to=2024-01-31"

# Balance
curl http://localhost:3000/accounts/ACC-12345/balance

# CSV export
curl "http://localhost:3000/transactions/export?format=csv"
```

> Note: with an empty store, a transfer from `ACC-12345` is recorded with
> `status: "failed"` (insufficient funds). Make a deposit to `ACC-12345` first,
> or start with `SEED=1`.

## 4. Run the tests

```bash
.venv/bin/pytest
```

Expected output: `26 passed`.

## Troubleshooting

- **`Address already in use`** — another process is on port 3000: use `PORT=8080 ./demo/run.sh`.
- **`ModuleNotFoundError: src`** — run commands from `homework-1/`, not from `src/`.
- **Permission denied on `run.sh`** — `chmod +x demo/run.sh` or run `bash demo/run.sh`.
