from fastapi import APIRouter, Depends, HTTPException
from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.schemas import BudgetCreate, BudgetUpdate
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/api/budgets", tags=["budgets"])

async def enrich_budget(b: dict, db) -> dict:
    cat = await db.categories.find_one({"_id": ObjectId(b["category_id"])}) if b.get("category_id") else None
    spent = b.get("spent_amount", 0)
    limit = b.get("limit_amount", 1)
    return {
        "id": str(b["_id"]),
        "category_id": b["category_id"],
        "category_name": cat["name"] if cat else "Unknown",
        "category_icon": cat.get("icon", "tag") if cat else "tag",
        "month_year": b["month_year"],
        "limit_amount": limit,
        "spent_amount": spent,
        "percentage": min((spent / limit) * 100, 100) if limit > 0 else 0,
    }

async def compute_spent(db, user_id: str, category_id: str, month_year: str) -> float:
    year, month = map(int, month_year.split("-"))
    start = datetime(year, month, 1)
    end = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
    pipeline = [
        {"$match": {"user_id": user_id, "category_id": category_id, "type": "expense",
                    "date": {"$gte": start, "$lt": end}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    result = await db.transactions.aggregate(pipeline).to_list(length=1)
    return result[0]["total"] if result else 0.0

@router.get("")
async def list_budgets(month_year: str = None, current_user=Depends(get_current_user)):
    db = get_db()
    user_id = str(current_user["_id"])
    if not month_year:
        now = datetime.utcnow()
        month_year = f"{now.year}-{now.month:02d}"
    
    budgets = await db.budgets.find({"user_id": user_id, "month_year": month_year}).to_list(length=100)
    
    # Update spent amounts
    for b in budgets:
        spent = await compute_spent(db, user_id, b["category_id"], month_year)
        await db.budgets.update_one({"_id": b["_id"]}, {"$set": {"spent_amount": spent}})
        b["spent_amount"] = spent
    
    return [await enrich_budget(b, db) for b in budgets]

@router.post("", status_code=201)
async def create_budget(data: BudgetCreate, current_user=Depends(get_current_user)):
    db = get_db()
    user_id = str(current_user["_id"])
    existing = await db.budgets.find_one({"user_id": user_id, "category_id": data.category_id, "month_year": data.month_year})
    if existing:
        raise HTTPException(status_code=400, detail="Budget already exists for this category and month")
    spent = await compute_spent(db, user_id, data.category_id, data.month_year)
    doc = data.model_dump()
    doc["user_id"] = user_id
    doc["spent_amount"] = spent
    doc["created_at"] = datetime.utcnow()
    result = await db.budgets.insert_one(doc)
    doc["_id"] = result.inserted_id
    return await enrich_budget(doc, db)

@router.put("/{budget_id}")
async def update_budget(budget_id: str, data: BudgetUpdate, current_user=Depends(get_current_user)):
    db = get_db()
    b = await db.budgets.find_one({"_id": ObjectId(budget_id), "user_id": str(current_user["_id"])})
    if not b:
        raise HTTPException(status_code=404, detail="Budget not found")
    await db.budgets.update_one({"_id": ObjectId(budget_id)}, {"$set": {"limit_amount": data.limit_amount}})
    updated = await db.budgets.find_one({"_id": ObjectId(budget_id)})
    return await enrich_budget(updated, db)

@router.delete("/{budget_id}", status_code=204)
async def delete_budget(budget_id: str, current_user=Depends(get_current_user)):
    db = get_db()
    result = await db.budgets.delete_one({"_id": ObjectId(budget_id), "user_id": str(current_user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Budget not found")
