from fastapi.testclient import TestClient
from main import app
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import DB_PATH

client = TestClient(app)


def setup_module():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    from database import create_tables
    create_tables()


def teardown_module():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


class TestExpenseTracker:
    def test_add_expense(self):
        response = client.post("/expenses", json={
            "amount": 25.50,
            "category": "Food",
            "description": "Lunch",
            "date": "2025-01-15",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == 25.50
        assert data["category"] == "Food"
        assert data["description"] == "Lunch"
        assert data["date"] == "2025-01-15"
        assert "id" in data

    def test_list_expenses(self):
        client.post("/expenses", json={"amount": 10, "category": "Transport", "date": "2025-01-16"})
        response = client.get("/expenses")
        assert response.status_code == 200
        assert len(response.json()) >= 2

    def test_list_expenses_filter_category(self):
        response = client.get("/expenses?category=Food")
        assert response.status_code == 200
        for e in response.json():
            assert e["category"] == "Food"

    def test_list_expenses_filter_date_range(self):
        response = client.get("/expenses?date_from=2025-01-01&date_to=2025-01-31")
        assert response.status_code == 200
        assert len(response.json()) >= 2

    def test_list_expenses_filter_from_to(self):
        response = client.get("/expenses?from=2025-01-01&to=2025-01-31")
        assert response.status_code == 200
        assert len(response.json()) >= 2
        for e in response.json():
            assert e["date"] >= "2025-01-01"
            assert e["date"] <= "2025-01-31"

    def test_get_single_expense(self):
        resp = client.post("/expenses", json={"amount": 99, "category": "Other", "date": "2025-02-01"})
        eid = resp.json()["id"]
        response = client.get(f"/expenses/{eid}")
        assert response.status_code == 200
        assert response.json()["amount"] == 99

    def test_get_expense_not_found(self):
        response = client.get("/expenses/99999")
        assert response.status_code == 404

    def test_update_expense(self):
        resp = client.post("/expenses", json={"amount": 50, "category": "Food", "date": "2025-03-01"})
        eid = resp.json()["id"]
        response = client.put(f"/expenses/{eid}", json={"amount": 75, "description": "Updated"})
        assert response.status_code == 200
        data = response.json()
        assert data["amount"] == 75
        assert data["description"] == "Updated"

    def test_update_expense_not_found(self):
        response = client.put("/expenses/99999", json={"amount": 10})
        assert response.status_code == 404

    def test_delete_expense(self):
        resp = client.post("/expenses", json={"amount": 1, "category": "Misc", "date": "2025-04-01"})
        eid = resp.json()["id"]
        response = client.delete(f"/expenses/{eid}")
        assert response.status_code == 204
        response = client.get(f"/expenses/{eid}")
        assert response.status_code == 404

    def test_delete_expense_not_found(self):
        response = client.delete("/expenses/99999")
        assert response.status_code == 404

    def test_summary(self):
        response = client.get("/summary")
        assert response.status_code == 200
        data = response.json()
        assert "by_category" in data
        assert "monthly" in data
        assert isinstance(data["by_category"], list)
        assert isinstance(data["monthly"], list)
