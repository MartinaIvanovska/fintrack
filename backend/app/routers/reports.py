from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from app.core.database import get_db
from app.core.security import get_current_user
from datetime import datetime
import io
import csv

router = APIRouter(prefix="/api/reports", tags=["reports"])

async def get_report_data(db, user_id: str, month_year: str) -> dict:
    year, month = map(int, month_year.split("-"))
    ms = datetime(year, month, 1)
    me = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)

    txs = await db.transactions.find({"user_id": user_id, "date": {"$gte": ms, "$lt": me}}).to_list(1000)
    income = sum(t["amount"] for t in txs if t["type"] == "income")
    expenses = sum(t["amount"] for t in txs if t["type"] == "expense")
    savings = income - expenses
    savings_rate = (savings / income * 100) if income > 0 else 0

    expense_txs = [t for t in txs if t["type"] == "expense"]
    largest = max(expense_txs, key=lambda x: x["amount"]) if expense_txs else None

    from bson import ObjectId
    cat_totals = {}
    for t in expense_txs:
        cid = t.get("category_id", "")
        cat_totals[cid] = cat_totals.get(cid, 0) + t["amount"]
    
    top_cat_id = max(cat_totals, key=cat_totals.get) if cat_totals else None
    top_cat = None
    if top_cat_id:
        try:
            top_cat = await db.categories.find_one({"_id": ObjectId(top_cat_id)})
        except:
            pass

    return {
        "month_year": month_year,
        "total_income": income,
        "total_expenses": expenses,
        "savings": savings,
        "savings_rate": savings_rate,
        "largest_expense": {"description": largest["description"], "amount": largest["amount"]} if largest else None,
        "top_spending_category": top_cat["name"] if top_cat else "N/A",
        "transactions": txs,
    }

@router.get("")
async def get_report(month_year: str = Query(default=None), current_user=Depends(get_current_user)):
    db = get_db()
    if not month_year:
        now = datetime.utcnow()
        month_year = f"{now.year}-{now.month:02d}"
    data = await get_report_data(db, str(current_user["_id"]), month_year)
    data.pop("transactions", None)
    return data

@router.get("/export/csv")
async def export_csv(month_year: str = Query(default=None), current_user=Depends(get_current_user)):
    db = get_db()
    if not month_year:
        now = datetime.utcnow()
        month_year = f"{now.year}-{now.month:02d}"
    data = await get_report_data(db, str(current_user["_id"]), month_year)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Type", "Description", "Amount", "Category", "Payment Method", "Merchant"])
    for tx in data["transactions"]:
        from bson import ObjectId
        cat = None
        try:
            cat = await db.categories.find_one({"_id": ObjectId(tx.get("category_id", ""))})
        except:
            pass
        writer.writerow([
            tx["date"].strftime("%Y-%m-%d"),
            tx["type"],
            tx["description"],
            tx["amount"],
            cat["name"] if cat else "Unknown",
            tx.get("payment_method", ""),
            tx.get("merchant", ""),
        ])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{month_year}.csv"}
    )
