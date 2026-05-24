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
BASE_EXPENSE = {"title": "Test", "amount": 10.0, "category": "food", "date": "2026-05-20"}


def _add_expense(overrides=None):
    data = {**BASE_EXPENSE, **(overrides or {})}
    return client.post("/expenses", json=data)


# === Health ===

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_health_response_structure():
    response = client.get("/health")
    assert isinstance(response.json(), dict)
    assert list(response.json().keys()) == ["status"]

# === CRUD: Create ===

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
    assert data["description"] == "Morning coffee"
    assert data["date"] == "2026-05-20"
    assert "id" in data

def test_add_expense_minimal():
    response = client.post("/expenses", json={
        "title": "Minimal",
        "amount": 5.0,
        "category": "test",
        "date": "2026-05-21"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Minimal"
    assert data["amount"] == 5.0
    assert data["description"] == ""

def test_add_expense_missing_title():
    resp = _add_expense({"title": None, "amount": 5.0, "category": "test", "date": "2026-05-21"})
    assert resp.status_code == 201
    assert resp.json()["title"] == ""

def test_add_expense_default_title():
    resp = client.post("/expenses", json={
        "amount": 25.0,
        "category": "food",
        "date": "2026-05-22"
    })
    assert resp.status_code == 201
    assert resp.json()["title"] == ""

def test_add_expense_zero_amount():
    resp = client.post("/expenses", json={
        "title": "Zero", "amount": 0, "category": "test", "date": "2026-05-21"
    })
    assert resp.status_code == 201
    assert resp.json()["amount"] == 0

def test_add_expense_negative_amount():
    resp = client.post("/expenses", json={
        "title": "Negative", "amount": -5.0, "category": "test", "date": "2026-05-21"
    })
    assert resp.status_code == 201
    assert resp.json()["amount"] == -5.0

def test_add_expense_empty_category():
    resp = client.post("/expenses", json={
        "title": "No cat", "amount": 5.0, "category": "", "date": "2026-05-21"
    })
    assert resp.status_code == 201

def test_add_expense_large_amount():
    resp = client.post("/expenses", json={
        "title": "Large", "amount": 999999.99, "category": "test", "date": "2026-05-21"
    })
    assert resp.status_code == 201
    assert resp.json()["amount"] == 999999.99

def test_add_expense_long_title():
    long_title = "A" * 100
    resp = client.post("/expenses", json={
        "title": long_title, "amount": 5.0, "category": "test", "date": "2026-05-21"
    })
    assert resp.status_code == 201
    assert resp.json()["title"] == long_title

def test_add_expense_very_long_title():
    resp = client.post("/expenses", json={
        "title": "A" * 101, "amount": 5.0, "category": "test", "date": "2026-05-21"
    })
    assert resp.status_code == 201
    assert len(resp.json()["title"]) == 101

def test_add_expense_special_chars():
    resp = client.post("/expenses", json={
        "title": "Café & Räume €100",
        "amount": 100.0,
        "category": "food",
        "description": "Special: üñîçödé",
        "date": "2026-05-21"
    })
    assert resp.status_code == 201
    assert resp.json()["title"] == "Café & Räume €100"

def test_add_expense_today_date():
    from datetime import date
    today = str(date.today())
    resp = client.post("/expenses", json={
        "title": "Today", "amount": 5.0, "category": "test", "date": today
    })
    assert resp.status_code == 201
    assert resp.json()["date"] == today

def test_add_expense_returns_created_expense():
    resp = _add_expense({"title": "ReturnCheck"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "ReturnCheck"
    assert isinstance(data["id"], int)
    assert data["id"] > 0

def test_add_expense_fields_match():
    payload = {"title": "Match", "amount": 42.5, "category": "utils", "description": "desc", "date": "2026-06-01"}
    resp = client.post("/expenses", json=payload)
    assert resp.status_code == 201
    for k, v in payload.items():
        assert resp.json()[k] == v

# === CRUD: Read / List ===

def test_list_expenses():
    response = client.get("/expenses")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_list_expenses_empty():
    _clean_db()
    resp = client.get("/expenses")
    assert resp.status_code == 200
    assert resp.json() == []

def test_list_returns_sorted_by_date_desc():
    _clean_db()
    client.post("/expenses", json={"title": "Older", "amount": 1, "category": "a", "date": "2026-01-01"})
    client.post("/expenses", json={"title": "Newer", "amount": 2, "category": "b", "date": "2026-06-01"})
    resp = client.get("/expenses")
    dates = [e["date"] for e in resp.json()]
    assert dates == sorted(dates, reverse=True)

def test_list_includes_all_fields():
    _clean_db()
    payload = {"title": "AllFields", "amount": 99.99, "category": "full", "description": "hello", "date": "2026-07-01"}
    created = client.post("/expenses", json=payload).json()
    resp = client.get("/expenses")
    item = resp.json()[0]
    for field in ["id", "title", "amount", "category", "description", "date"]:
        assert field in item

def test_get_expense():
    resp = _add_expense({"title": "GetTest"})
    expense_id = resp.json()["id"]
    response = client.get(f"/expenses/{expense_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "GetTest"

def test_get_expense_not_found():
    response = client.get("/expenses/999999")
    assert response.status_code == 404

def test_get_expense_invalid_id():
    response = client.get("/expenses/abc")
    assert response.status_code == 422

def test_get_expense_zero_id():
    response = client.get("/expenses/0")
    assert response.status_code == 404

def test_get_after_delete_returns_404():
    _clean_db()
    created = _add_expense({"title": "DelMe"}).json()
    client.delete(f"/expenses/{created['id']}")
    resp = client.get(f"/expenses/{created['id']}")
    assert resp.status_code == 404

def test_list_after_delete():
    _clean_db()
    c1 = _add_expense({"title": "A"}).json()
    _add_expense({"title": "B"})
    client.delete(f"/expenses/{c1['id']}")
    resp = client.get("/expenses")
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "B"

def test_get_expense_returns_correct_id():
    _clean_db()
    e1 = _add_expense({"title": "First"}).json()
    e2 = _add_expense({"title": "Second"}).json()
    assert client.get(f"/expenses/{e1['id']}").json()["title"] == "First"
    assert client.get(f"/expenses/{e2['id']}").json()["title"] == "Second"

# === CRUD: Update ===

def test_update_expense():
    resp = _add_expense({"title": "Old"})
    expense_id = resp.json()["id"]
    response = client.put(f"/expenses/{expense_id}", json={"title": "New"})
    assert response.status_code == 200
    assert response.json()["title"] == "New"

def test_update_expense_all_fields():
    created = _add_expense({"title": "Orig"}).json()
    update = {"title": "Updated", "amount": 99.0, "category": "newcat", "description": "new desc", "date": "2026-12-01"}
    resp = client.put(f"/expenses/{created['id']}", json=update)
    assert resp.status_code == 200
    for k, v in update.items():
        assert resp.json()[k] == v

def test_update_expense_partial_amount():
    created = _add_expense({"title": "Partial", "amount": 10.0}).json()
    resp = client.put(f"/expenses/{created['id']}", json={"amount": 25.0})
    assert resp.status_code == 200
    assert resp.json()["amount"] == 25.0
    assert resp.json()["title"] == "Partial"

def test_update_expense_partial_category():
    created = _add_expense({"category": "oldcat"}).json()
    resp = client.put(f"/expenses/{created['id']}", json={"category": "newcat"})
    assert resp.status_code == 200
    assert resp.json()["category"] == "newcat"

def test_update_expense_partial_date():
    created = _add_expense({"date": "2026-01-01"}).json()
    resp = client.put(f"/expenses/{created['id']}", json={"date": "2026-12-31"})
    assert resp.status_code == 200
    assert resp.json()["date"] == "2026-12-31"

def test_update_expense_empty_body():
    created = _add_expense({"title": "EmptyBody"}).json()
    resp = client.put(f"/expenses/{created['id']}", json={})
    assert resp.status_code == 200

def test_update_expense_not_found():
    response = client.put("/expenses/99999", json={"title": "Nope"})
    assert response.status_code == 404

def test_update_expense_clear_description():
    created = _add_expense({"description": "something"}).json()
    resp = client.put(f"/expenses/{created['id']}", json={"description": ""})
    assert resp.status_code == 200
    assert resp.json()["description"] == ""

def test_update_expense_title_to_empty():
    created = _add_expense({"title": "NotEmpty"}).json()
    resp = client.put(f"/expenses/{created['id']}", json={"title": ""})
    assert resp.status_code == 200

# === CRUD: Delete ===

def test_delete_expense():
    resp = _add_expense({"title": "Delete me"})
    expense_id = resp.json()["id"]
    response = client.delete(f"/expenses/{expense_id}")
    assert response.status_code == 204
    response = client.get(f"/expenses/{expense_id}")
    assert response.status_code == 404

def test_delete_expense_not_found():
    response = client.delete("/expenses/99999")
    assert response.status_code == 404

def test_delete_expense_twice():
    created = _add_expense({"title": "DoubleDel"}).json()
    client.delete(f"/expenses/{created['id']}")
    resp = client.delete(f"/expenses/{created['id']}")
    assert resp.status_code == 404

def test_delete_large_id():
    resp = client.delete("/expenses/999999999")
    assert resp.status_code == 404

# === Filtering ===

def test_filter_by_category():
    _clean_db()
    client.post("/expenses", json={"title": "Food", "amount": 15.0, "category": "food", "date": "2026-05-20"})
    response = client.get("/expenses?category=food")
    assert response.status_code == 200
    for item in response.json():
        assert item["category"] == "food"

def test_filter_by_category_no_match():
    resp = client.get("/expenses?category=nonexistent")
    assert resp.status_code == 200
    assert resp.json() == []

def test_filter_by_date_from():
    _clean_db()
    client.post("/expenses", json={"title": "Old", "amount": 1, "category": "t", "date": "2026-01-01"})
    client.post("/expenses", json={"title": "New", "amount": 2, "category": "t", "date": "2026-06-01"})
    resp = client.get("/expenses?from=2026-03-01")
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "New"

def test_filter_by_date_to():
    resp = client.get("/expenses?to=2026-02-01")
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "Old"

def test_filter_by_date_range():
    resp = client.get("/expenses?date_from=2026-01-01&date_to=2026-12-31")
    assert resp.status_code == 200

def test_filter_by_category_and_date():
    _clean_db()
    client.post("/expenses", json={"title": "A", "amount": 1, "category": "food", "date": "2026-05-01"})
    client.post("/expenses", json={"title": "B", "amount": 2, "category": "food", "date": "2026-06-01"})
    client.post("/expenses", json={"title": "C", "amount": 3, "category": "other", "date": "2026-05-01"})
    resp = client.get("/expenses?category=food&from=2026-05-15")
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "B"

# === Summary ===

def test_summary():
    response = client.get("/summary")
    assert response.status_code == 200
    data = response.json()
    assert "by_category" in data
    assert "monthly" in data

def test_summary_empty_db():
    _clean_db()
    resp = client.get("/summary")
    assert resp.status_code == 200
    assert resp.json()["by_category"] == []
    assert resp.json()["monthly"] == []

def test_summary_by_category():
    _clean_db()
    client.post("/expenses", json={"title": "A", "amount": 100, "category": "food", "date": "2026-05-01"})
    client.post("/expenses", json={"title": "B", "amount": 50, "category": "food", "date": "2026-05-02"})
    client.post("/expenses", json={"title": "C", "amount": 30, "category": "transport", "date": "2026-05-03"})
    resp = client.get("/summary")
    cat = {c["category"]: c["total"] for c in resp.json()["by_category"]}
    assert cat["food"] == 150
    assert cat["transport"] == 30

def test_summary_monthly():
    _clean_db()
    client.post("/expenses", json={"title": "M1", "amount": 10, "category": "a", "date": "2026-01-15"})
    client.post("/expenses", json={"title": "M2", "amount": 20, "category": "b", "date": "2026-02-10"})
    resp = client.get("/summary")
    months = {m["month"]: m["total"] for m in resp.json()["monthly"]}
    assert months["2026-01"] == 10
    assert months["2026-02"] == 20

def test_summary_aggregates_multiple_months():
    _clean_db()
    for m in range(1, 7):
        client.post("/expenses", json={
            "title": f"M{m}", "amount": float(m * 10),
            "category": "test", "date": f"2026-{m:02d}-01"
        })
    resp = client.get("/summary")
    assert len(resp.json()["monthly"]) == 6

def test_summary_response_structure():
    resp = client.get("/summary")
    data = resp.json()
    assert isinstance(data["by_category"], list)
    assert isinstance(data["monthly"], list)
    for item in data["by_category"]:
        assert "category" in item
        assert "total" in item
    for item in data["monthly"]:
        assert "month" in item
        assert "total" in item

# === Frontend serving ===

def test_frontend_serves_index():
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert "<!DOCTYPE html>" in html
    assert "Folio" in html
    assert "Expense Tracker" in html

def test_frontend_index_contains_sidebar():
    resp = client.get("/")
    assert "sidebar" in resp.text or "sidebar" in resp.text.lower()

def test_frontend_index_contains_graph_view():
    resp = client.get("/")
    assert "graph-view" in resp.text or "graph" in resp.text.lower()

def test_frontend_index_contains_design_tokens():
    resp = client.get("/")
    html = resp.text
    tokens = ["--bg-primary", "--bg-secondary", "--accent-primary", "--font-sans", "--sidebar-width"]
    for token in tokens:
        assert token in html, f"Missing design token: {token}"

def test_frontend_index_has_css_custom_properties():
    resp = client.get("/")
    assert ":root" in resp.text

def test_frontend_index_has_style_block():
    resp = client.get("/")
    assert "<style>" in resp.text
    assert "</style>" in resp.text

def test_frontend_index_has_toast_system():
    resp = client.get("/")
    assert "toast" in resp.text.lower()

def test_frontend_index_has_skeleton_loaders():
    resp = client.get("/")
    assert "skeleton" in resp.text.lower()

def test_frontend_index_has_hotkey_modal():
    resp = client.get("/")
    assert "hotkey" in resp.text.lower()

def test_frontend_index_has_d3_cdn():
    resp = client.get("/")
    assert "d3js.org" in resp.text

def test_frontend_index_has_three_panel_layout():
    resp = client.get("/")
    html = resp.text
    assert "#sidebar" in html
    assert "#note-list" in html or "note-list" in html
    assert "#editor" in html or "editor" in html

def test_frontend_serves_subpath_returns_index():
    resp = client.get("/some/nonexistent/path")
    assert resp.status_code == 200
    assert "Folio" in resp.text

def test_frontend_known_404():
    resp = client.get("/api/nonexistent")
    assert resp.status_code == 200
    assert "Folio" in resp.text


# === Helper ===

def _clean_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    create_tables()
