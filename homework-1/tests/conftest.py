import pytest
from fastapi.testclient import TestClient

from src.app import create_app
from src.storage.memory import store


@pytest.fixture()
def client():
    store.clear()
    with TestClient(create_app()) as test_client:
        yield test_client
    store.clear()


def deposit(client, account="ACC-12345", amount=500, currency="USD"):
    response = client.post(
        "/transactions",
        json={"toAccount": account, "amount": amount, "currency": currency, "type": "deposit"},
    )
    assert response.status_code == 201, response.text
    return response.json()
