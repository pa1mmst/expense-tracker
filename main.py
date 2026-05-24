from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Optional
from contextlib import asynccontextmanager
from pathlib import Path
from database import get_connection, create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="Expense Tracker", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


def expense_from_row(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "amount": row["amount"],
        "category": row["category"],
        "description": row["description"],
        "date": row["date"],
    }


@app.post("/expenses", status_code=201)
def add_expense(expense: dict):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO expenses (title, amount, category, description, date) VALUES (?, ?, ?, ?, ?)",
        (expense.get("title") or "", expense.get("amount"), expense.get("category") or "", expense.get("description") or "", expense.get("date")),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return expense_from_row(row)


@app.get("/expenses")
def list_expenses(
    category: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    date_from: Optional[str] = Query(None, alias="date_from"),
    date_to: Optional[str] = Query(None, alias="date_to"),
):
    query = "SELECT * FROM expenses WHERE 1=1"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)
    if from_date:
        query += " AND date >= ?"
        params.append(from_date)
    if to_date:
        query += " AND date <= ?"
        params.append(to_date)
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)

    query += " ORDER BY date DESC"
    conn = get_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [expense_from_row(r) for r in rows]


@app.get("/expenses/{expense_id}")
def get_expense(expense_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense_from_row(row)


@app.put("/expenses/{expense_id}")
def update_expense(expense_id: int, expense: dict):
    conn = get_connection()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Expense not found")

    fields = {"title", "amount", "category", "description", "date"}
    updates = {k: v for k, v in expense.items() if k in fields and v is not None}

    if not updates:
        conn.close()
        return expense_from_row(row)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [expense_id]

    conn.execute(f"UPDATE expenses SET {set_clause} WHERE id = ?", values)
    conn.commit()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    return expense_from_row(row)


@app.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Expense not found")
    conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()


@app.get("/summary")
def get_summary():
    conn = get_connection()

    by_category_rows = conn.execute(
        "SELECT category, SUM(amount) as total FROM expenses GROUP BY category ORDER BY category"
    ).fetchall()

    monthly_rows = conn.execute(
        "SELECT strftime('%Y-%m', date) as month, SUM(amount) as total FROM expenses GROUP BY month ORDER BY month"
    ).fetchall()

    conn.close()

    return {
        "by_category": [{"category": r["category"], "total": r["total"]} for r in by_category_rows],
        "monthly": [{"month": r["month"], "total": r["total"]} for r in monthly_rows],
    }


static_dir = Path(__file__).parent / "static"


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if static_dir.exists():
        file_path = static_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
    raise HTTPException(status_code=404, detail="Not found")
