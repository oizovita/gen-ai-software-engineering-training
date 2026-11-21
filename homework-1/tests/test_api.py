"""End-to-end tests for the Banking Transactions API (run with `pytest`)."""

from tests.conftest import deposit

TRANSFER = {
    "fromAccount": "ACC-12345",
    "toAccount": "ACC-67890",
    "amount": 100.50,
    "currency": "USD",
    "type": "transfer",
}


# --- Task 1: core endpoints -------------------------------------------------


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_create_transaction_returns_201_with_generated_fields(client):
    deposit(client)
    response = client.post("/transactions", json=TRANSFER)
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["timestamp"].endswith("Z")
    assert body["status"] == "completed"
    assert body["amount"] == 100.5
    assert body["fromAccount"] == "ACC-12345"
    assert body["toAccount"] == "ACC-67890"


def test_list_transactions(client):
    deposit(client)
    client.post("/transactions", json=TRANSFER)
    response = client.get("/transactions")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_transaction_by_id(client):
    created = deposit(client)
    response = client.get(f"/transactions/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_transaction_returns_404(client):
    response = client.get("/transactions/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"error": "Transaction not found"}


def test_balance_counts_only_completed_transactions(client):
    deposit(client, amount=500)
    client.post("/transactions", json=TRANSFER)  # -100.50 completed
    client.post(  # exceeds balance -> failed, must not affect balance
        "/transactions",
        json={"fromAccount": "ACC-12345", "amount": 10_000, "currency": "USD", "type": "withdrawal"},
    )
    assert client.get("/accounts/ACC-12345/balance").json()["balance"] == 399.5
    assert client.get("/accounts/ACC-67890/balance").json()["balance"] == 100.5


def test_balance_unknown_account_returns_404(client):
    response = client.get("/accounts/ACC-00000/balance")
    assert response.status_code == 404
    assert response.json() == {"error": "Account not found"}


def test_balance_invalid_account_format_returns_400(client):
    response = client.get("/accounts/not-an-account/balance")
    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == "accountId"


def test_insufficient_funds_marks_transaction_failed(client):
    response = client.post(
        "/transactions",
        json={"fromAccount": "ACC-12345", "amount": 1, "currency": "USD", "type": "withdrawal"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "failed"


def test_invalid_json_body_returns_400(client):
    response = client.post(
        "/transactions", content="{oops", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400
    assert response.json()["error"] == "Validation failed"


# --- Task 2: validation ------------------------------------------------------


def _fields(response):
    return {d["field"] for d in response.json()["details"]}


def test_validation_error_format_matches_spec(client):
    response = client.post("/transactions", json={**TRANSFER, "amount": -10, "currency": "XYZ"})
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "Validation failed"
    assert {"field": "amount", "message": "Amount must be a positive number"} in body["details"]
    assert {"field": "currency", "message": "Invalid currency code"} in body["details"]


def test_amount_must_be_positive_number(client):
    for bad in (0, -1, "100", True, None):
        response = client.post("/transactions", json={**TRANSFER, "amount": bad})
        assert response.status_code == 400, bad
        assert "amount" in _fields(response)


def test_amount_max_two_decimals(client):
    response = client.post("/transactions", json={**TRANSFER, "amount": 10.123})
    assert response.status_code == 400
    assert response.json()["details"] == [
        {"field": "amount", "message": "Amount must have at most 2 decimal places"}
    ]


def test_account_format(client):
    response = client.post(
        "/transactions", json={**TRANSFER, "fromAccount": "12345", "toAccount": "ACC-1234"}
    )
    assert response.status_code == 400
    assert _fields(response) == {"fromAccount", "toAccount"}


def test_currency_is_case_insensitive_and_normalized(client):
    response = client.post("/transactions", json={**TRANSFER, "currency": "usd"})
    assert response.status_code == 201
    assert response.json()["currency"] == "USD"


def test_type_must_be_known(client):
    response = client.post("/transactions", json={**TRANSFER, "type": "refund"})
    assert response.status_code == 400
    assert "type" in _fields(response)


def test_required_accounts_depend_on_type(client):
    cases = [
        ({"amount": 1, "currency": "USD", "type": "deposit"}, {"toAccount"}),
        ({"amount": 1, "currency": "USD", "type": "withdrawal"}, {"fromAccount"}),
        ({"amount": 1, "currency": "USD", "type": "transfer"}, {"fromAccount", "toAccount"}),
        ({**TRANSFER, "toAccount": "ACC-12345"}, {"toAccount"}),  # same account
    ]
    for payload, expected in cases:
        response = client.post("/transactions", json=payload)
        assert response.status_code == 400, payload
        assert _fields(response) == expected, payload


def test_all_errors_reported_together(client):
    response = client.post(
        "/transactions",
        json={"fromAccount": "x", "toAccount": "y", "amount": -1, "currency": "???", "type": "nope"},
    )
    assert _fields(response) == {"fromAccount", "toAccount", "amount", "currency", "type"}


# --- Task 3: filters ---------------------------------------------------------


def _seed_history(client):
    deposit(client, "ACC-12345", 1000)
    deposit(client, "ACC-67890", 300)
    client.post("/transactions", json=TRANSFER)
    client.post(
        "/transactions",
        json={"fromAccount": "ACC-67890", "amount": 50, "currency": "USD", "type": "withdrawal"},
    )


def test_filter_by_account_matches_from_or_to(client):
    _seed_history(client)
    rows = client.get("/transactions", params={"accountId": "ACC-67890"}).json()
    assert len(rows) == 3
    assert all("ACC-67890" in (r["fromAccount"], r["toAccount"]) for r in rows)


def test_filter_by_type(client):
    _seed_history(client)
    rows = client.get("/transactions", params={"type": "deposit"}).json()
    assert [r["type"] for r in rows] == ["deposit", "deposit"]


def test_filter_by_date_range(client):
    _seed_history(client)
    today = client.get("/transactions").json()[0]["timestamp"][:10]
    assert len(client.get("/transactions", params={"from": today, "to": today}).json()) == 4
    assert client.get("/transactions", params={"from": "2000-01-01", "to": "2000-12-31"}).json() == []
    assert len(client.get("/transactions", params={"from": "2000-01-01T00:00:00Z"}).json()) == 4


def test_combined_filters(client):
    _seed_history(client)
    today = client.get("/transactions").json()[0]["timestamp"][:10]
    rows = client.get(
        "/transactions",
        params={"accountId": "ACC-12345", "type": "transfer", "from": today, "to": today},
    ).json()
    assert len(rows) == 1
    assert rows[0]["amount"] == 100.5


def test_invalid_filters_return_400(client):
    response = client.get(
        "/transactions", params={"type": "refund", "from": "2024-13-01", "accountId": "bad"}
    )
    assert response.status_code == 400
    assert _fields(response) == {"type", "from", "accountId"}
    response = client.get("/transactions", params={"from": "2024-02-01", "to": "2024-01-01"})
    assert response.status_code == 400
    assert _fields(response) == {"to"}


# --- Task 4C: CSV export -----------------------------------------------------


def test_csv_export(client):
    _seed_history(client)
    response = client.get("/transactions/export", params={"format": "csv"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'filename="transactions.csv"' in response.headers["content-disposition"]
    lines = response.text.strip().split("\n")
    assert lines[0] == "id,fromAccount,toAccount,amount,currency,type,timestamp,status"
    assert len(lines) == 5
    assert ",ACC-12345,ACC-67890,100.50,USD,transfer," in lines[3]
    assert lines[1].split(",")[1] == ""  # deposit has no fromAccount


def test_csv_export_respects_filters(client):
    _seed_history(client)
    response = client.get("/transactions/export", params={"format": "csv", "type": "withdrawal"})
    lines = response.text.strip().split("\n")
    assert len(lines) == 2
    assert ",withdrawal," in lines[1]


def test_csv_export_unsupported_format(client):
    response = client.get("/transactions/export", params={"format": "xml"})
    assert response.status_code == 400
    assert _fields(response) == {"format"}
