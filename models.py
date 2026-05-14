from pydantic import BaseModel, Field
from typing import Optional
from datetime import date as date_type


class ExpenseCreate(BaseModel):
    amount: float = Field(..., gt=0)
    category: str = Field(..., min_length=1)
    description: str = ""
    date: str = Field(default_factory=lambda: str(date_type.today()))


class ExpenseUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    category: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    date: Optional[str] = None


class ExpenseResponse(BaseModel):
    id: int
    amount: float
    category: str
    description: str
    date: str


class CategorySummary(BaseModel):
    category: str
    total: float


class MonthlySummary(BaseModel):
    month: str
    total: float


class SummaryResponse(BaseModel):
    by_category: list[CategorySummary]
    monthly: list[MonthlySummary]
