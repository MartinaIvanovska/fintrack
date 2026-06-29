from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# --- Auth ---
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    username: str
    email: str
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

# --- Transactions ---
class TransactionType(str, Enum):
    income = "income"
    expense = "expense"

class TransactionCreate(BaseModel):
    type: TransactionType
    amount: float = Field(gt=0)
    date: datetime
    category_id: str
    description: str
    payment_method: Optional[str] = None
    merchant: Optional[str] = None
    notes: Optional[str] = None
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None

class TransactionUpdate(BaseModel):
    amount: Optional[float] = Field(default=None, gt=0)
    date: Optional[datetime] = None
    category_id: Optional[str] = None
    description: Optional[str] = None
    payment_method: Optional[str] = None
    merchant: Optional[str] = None
    notes: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurrence_rule: Optional[str] = None

class TransactionOut(BaseModel):
    id: str
    type: str
    amount: float
    date: datetime
    category_id: str
    category_name: Optional[str] = None
    description: str
    payment_method: Optional[str] = None
    merchant: Optional[str] = None
    notes: Optional[str] = None
    is_recurring: bool
    recurrence_rule: Optional[str] = None

# --- Categories ---
class CategoryCreate(BaseModel):
    name: str
    type: TransactionType
    icon: Optional[str] = "tag"

class CategoryOut(BaseModel):
    id: str
    name: str
    type: str
    icon: Optional[str]
    is_default: bool

# --- Budgets ---
class BudgetCreate(BaseModel):
    category_id: str
    month_year: str  # "YYYY-MM"
    limit_amount: float = Field(gt=0)

class BudgetUpdate(BaseModel):
    limit_amount: float = Field(gt=0)

class BudgetOut(BaseModel):
    id: str
    category_id: str
    category_name: Optional[str] = None
    month_year: str
    limit_amount: float
    spent_amount: float
    percentage: float

# --- Dashboard ---
class DashboardResponse(BaseModel):
    total_income: float
    total_expenses: float
    remaining_balance: float
    savings_rate: float
    spending_by_category: List[dict]
    monthly_trend: List[dict]
    income_vs_expenses: List[dict]
    recent_transactions: List[dict]
