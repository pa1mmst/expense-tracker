import pytest
import os
from fastapi.testclient import TestClient
from main import app
from database import create_tables, DB_PATH

# Clean DB and create tables before tests
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
create_tables()

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_add_expense():
    response = client.post("/expenses", json={
        "title": "Coffee",
        "amount": 3.50,
        "category": "food",
        "description": "Morning coffee",
        "date": "2026-05-20"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Coffee"
    assert data["amount"] == 3.50
    assert data["category"] == "food"


def test_list_expenses():
    response = client.get("/expenses")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_expense():
    resp = client.post("/expenses", json={
        "title": "Test",
        "amount": 10.0,
        "category": "test",
        "date": "2026-05-20"
    })
    expense_id = resp.json()["id"]
    response = client.get(f"/expenses/{expense_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Test"


def test_update_expense():
    resp = client.post("/expenses", json={
        "title": "Old",
        "amount": 5.0,
        "category": "test",
        "date": "2026-05-20"
    })
    expense_id = resp.json()["id"]
    response = client.put(f"/expenses/{expense_id}", json={"title": "New"})
    assert response.status_code == 200
    assert response.json()["title"] == "New"


def test_delete_expense():
    resp = client.post("/expenses", json={
        "title": "Delete me",
        "amount": 1.0,
        "category": "test",
        "date": "2026-05-20"
    })
    expense_id = resp.json()["id"]
    response = client.delete(f"/expenses/{expense_id}")
    assert response.status_code == 204
    response = client.get(f"/expenses/{expense_id}")
    assert response.status_code == 404


def test_filter_by_category():
    client.post("/expenses", json={
        "title": "Food item",
        "amount": 15.0,
        "category": "food",
        "date": "2026-05-20"
    })
    response = client.get("/expenses?category=food")
    assert response.status_code == 200
    for item in response.json():
        assert item["category"] == "food"


def test_summary():
    response = client.get("/summary")
    assert response.status_code == 200
    data = response.json()
    assert "by_category" in data
    assert "monthly" in data
