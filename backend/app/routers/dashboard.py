from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.core.security import get_current_user
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("")
async def get_dashboard(current_user=Depends(get_current_user)):
    db = get_db()
    user_id = str(current_user["_id"])
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    month_end = datetime(now.year, now.month + 1, 1) if now.month < 12 else datetime(now.year + 1, 1, 1)

    # Total income & expenses for current month
    income_pipeline = [
        {"$match": {"user_id": user_id, "type": "income", "date": {"$gte": month_start, "$lt": month_end}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    expense_pipeline = [
        {"$match": {"user_id": user_id, "type": "expense", "date": {"$gte": month_start, "$lt": month_end}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    income_result = await db.transactions.aggregate(income_pipeline).to_list(1)
    expense_result = await db.transactions.aggregate(expense_pipeline).to_list(1)
    total_income = income_result[0]["total"] if income_result else 0.0
    total_expenses = expense_result[0]["total"] if expense_result else 0.0
    remaining = total_income - total_expenses
    savings_rate = (remaining / total_income * 100) if total_income > 0 else 0.0

    # Spending by category
    cat_pipeline = [
        {"$match": {"user_id": user_id, "type": "expense", "date": {"$gte": month_start, "$lt": month_end}}},
        {"$group": {"_id": "$category_id", "total": {"$sum": "$amount"}}},
        {"$sort": {"total": -1}},
        {"$limit": 8}
    ]
    cat_results = await db.transactions.aggregate(cat_pipeline).to_list(8)
    spending_by_category = []
    for r in cat_results:
        from bson import ObjectId
        cat = await db.categories.find_one({"_id": ObjectId(r["_id"])}) if r["_id"] else None
        spending_by_category.append({"name": cat["name"] if cat else "Other", "value": r["total"]})

    # Monthly trend (last 6 months)
    monthly_trend = []
    income_vs_expenses = []
    for i in range(5, -1, -1):
        d = datetime(now.year, now.month, 1)
        month_num = now.month - i
        year = now.year
        while month_num <= 0:
            month_num += 12
            year -= 1
        ms = datetime(year, month_num, 1)
        me = datetime(year, month_num + 1, 1) if month_num < 12 else datetime(year + 1, 1, 1)
        
        inc_r = await db.transactions.aggregate([
            {"$match": {"user_id": user_id, "type": "income", "date": {"$gte": ms, "$lt": me}}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]).to_list(1)
        exp_r = await db.transactions.aggregate([
            {"$match": {"user_id": user_id, "type": "expense", "date": {"$gte": ms, "$lt": me}}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]).to_list(1)
        
        inc = inc_r[0]["total"] if inc_r else 0
        exp = exp_r[0]["total"] if exp_r else 0
        label = ms.strftime("%b")
        monthly_trend.append({"month": label, "expenses": exp})
        income_vs_expenses.append({"month": label, "income": inc, "expenses": exp, "savings": max(inc - exp, 0)})

    # Recent transactions
    recent_txs = await db.transactions.find({"user_id": user_id}).sort("date", -1).limit(5).to_list(5)
    recent_out = []
    for tx in recent_txs:
        from bson import ObjectId
        cat = await db.categories.find_one({"_id": ObjectId(tx["category_id"])}) if tx.get("category_id") else None
        recent_out.append({
            "id": str(tx["_id"]),
            "description": tx["description"],
            "amount": tx["amount"],
            "type": tx["type"],
            "date": tx["date"].isoformat(),
            "category_name": cat["name"] if cat else "Other",
            "category_icon": cat.get("icon", "tag") if cat else "tag",
        })

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "remaining_balance": remaining,
        "savings_rate": savings_rate,
        "spending_by_category": spending_by_category,
        "monthly_trend": monthly_trend,
        "income_vs_expenses": income_vs_expenses,
        "recent_transactions": recent_out,
    }
