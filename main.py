from fastapi import FastAPI, HTTPException, Query
from typing import Optional
from contextlib import asynccontextmanager
from database import get_connection, create_tables
from models import ExpenseCreate, ExpenseUpdate, ExpenseResponse, SummaryResponse, CategorySummary, MonthlySummary


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="Expense Tracker", lifespan=lifespan)


def expense_from_row(row) -> dict:
    return {
        "id": row["id"],
        "amount": row["amount"],
        "category": row["category"],
        "description": row["description"],
        "date": row["date"],
    }


@app.post("/expenses", response_model=ExpenseResponse, status_code=201)
def add_expense(expense: ExpenseCreate):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO expenses (amount, category, description, date) VALUES (?, ?, ?, ?)",
        (expense.amount, expense.category, expense.description, expense.date),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return expense_from_row(row)


@app.get("/expenses", response_model=list[ExpenseResponse])
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


@app.get("/expenses/{expense_id}", response_model=ExpenseResponse)
def get_expense(expense_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense_from_row(row)


@app.put("/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(expense_id: int, expense: ExpenseUpdate):
    conn = get_connection()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Expense not found")

    fields = {"amount", "category", "description", "date"}
    updates = {k: getattr(expense, k) for k in fields if getattr(expense, k) is not None}

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


@app.get("/summary", response_model=SummaryResponse)
def get_summary():
    conn = get_connection()

    by_category_rows = conn.execute(
        "SELECT category, SUM(amount) as total FROM expenses GROUP BY category ORDER BY category"
    ).fetchall()

    monthly_rows = conn.execute(
        "SELECT strftime('%Y-%m', date) as month, SUM(amount) as total FROM expenses GROUP BY month ORDER BY month"
    ).fetchall()

    conn.close()

    return SummaryResponse(
        by_category=[CategorySummary(category=r["category"], total=r["total"]) for r in by_category_rows],
        monthly=[MonthlySummary(month=r["month"], total=r["total"]) for r in monthly_rows],
    )
