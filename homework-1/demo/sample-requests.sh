#!/usr/bin/env bash
# Sample API calls (curl). Start the API first: ./demo/run.sh
# Usage: bash demo/sample-requests.sh [base_url]
set -u
BASE="${1:-http://localhost:3000}"
H='Content-Type: application/json'

step() { printf '\n\033[1;34m# %s\033[0m\n' "$1"; }
call() { curl -s -w '\n→ HTTP %{http_code}\n' "$@"; }

step "Task 1: deposit 500 USD to ACC-12345 (201)"
call -X POST "$BASE/transactions" -H "$H" \
  -d '{"toAccount":"ACC-12345","amount":500,"currency":"USD","type":"deposit"}'

step "Task 1: transfer 100.50 USD ACC-12345 -> ACC-67890 (201, completed)"
TX=$(curl -s -X POST "$BASE/transactions" -H "$H" \
  -d '{"fromAccount":"ACC-12345","toAccount":"ACC-67890","amount":100.50,"currency":"USD","type":"transfer"}')
echo "$TX"
TX_ID=$(echo "$TX" | sed -E 's/.*"id":"([^"]+)".*/\1/')

step "Task 1: withdrawal exceeding balance (201, status=failed, balance unchanged)"
call -X POST "$BASE/transactions" -H "$H" \
  -d '{"fromAccount":"ACC-67890","amount":9999,"currency":"USD","type":"withdrawal"}'

step "Task 1: list all transactions (200)"
call "$BASE/transactions"

step "Task 1: get transaction by id (200)"
call "$BASE/transactions/$TX_ID"

step "Task 1: unknown transaction (404)"
call "$BASE/transactions/does-not-exist"

step "Task 1: account balance (200)"
call "$BASE/accounts/ACC-12345/balance"
call "$BASE/accounts/ACC-67890/balance"

step "Task 1: unknown account (404)"
call "$BASE/accounts/ACC-00000/balance"

step "Task 2: validation errors (400) - bad amount, currency, account format"
call -X POST "$BASE/transactions" -H "$H" \
  -d '{"fromAccount":"12345","toAccount":"ACC-6789","amount":-10,"currency":"XYZ","type":"transfer"}'

step "Task 2: amount with 3 decimals (400)"
call -X POST "$BASE/transactions" -H "$H" \
  -d '{"toAccount":"ACC-12345","amount":10.123,"currency":"USD","type":"deposit"}'

step "Task 3: filter by account"
call "$BASE/transactions?accountId=ACC-12345"

step "Task 3: filter by type"
call "$BASE/transactions?type=transfer"

step "Task 3: filter by date range (today)"
TODAY=$(date -u +%Y-%m-%d)
call "$BASE/transactions?from=$TODAY&to=$TODAY"

step "Task 3: combined filters"
call "$BASE/transactions?accountId=ACC-12345&type=transfer&from=$TODAY&to=$TODAY"

step "Task 3: invalid filters (400)"
call "$BASE/transactions?type=refund&from=2024-13-01"

step "Task 4C: CSV export"
call "$BASE/transactions/export?format=csv"

step "Task 4C: CSV export with filter"
call "$BASE/transactions/export?format=csv&type=deposit"

step "Task 4C: unsupported format (400)"
call "$BASE/transactions/export?format=xml"
