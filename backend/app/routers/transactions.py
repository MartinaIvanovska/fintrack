from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.schemas import TransactionCreate, TransactionUpdate, TransactionOut
from bson import ObjectId
from datetime import datetime
from typing import Optional, List

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

async def enrich_transaction(tx: dict, db) -> dict:
    cat = await db.categories.find_one({"_id": ObjectId(tx["category_id"])}) if tx.get("category_id") else None
    return {
        "id": str(tx["_id"]),
        "type": tx["type"],
        "amount": tx["amount"],
        "date": tx["date"],
        "category_id": tx.get("category_id", ""),
        "category_name": cat["name"] if cat else "Unknown",
        "description": tx["description"],
        "payment_method": tx.get("payment_method"),
        "merchant": tx.get("merchant"),
        "notes": tx.get("notes"),
        "is_recurring": tx.get("is_recurring", False),
        "recurrence_rule": tx.get("recurrence_rule"),
    }

@router.get("")
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    type: Optional[str] = None,
    category_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_by: str = "date",
    sort_order: str = "desc",
    current_user=Depends(get_current_user)
):
    db = get_db()
    user_id = str(current_user["_id"])
    
    query = {"user_id": user_id}
    if search:
        query["$or"] = [
            {"description": {"$regex": search, "$options": "i"}},
            {"merchant": {"$regex": search, "$options": "i"}},
        ]
    if type:
        query["type"] = type
    if category_id:
        query["category_id"] = category_id
    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter["$gte"] = datetime.fromisoformat(start_date)
        if end_date:
            date_filter["$lte"] = datetime.fromisoformat(end_date)
        query["date"] = date_filter

    sort_dir = -1 if sort_order == "desc" else 1
    total = await db.transactions.count_documents(query)
    cursor = db.transactions.find(query).sort(sort_by, sort_dir).skip((page - 1) * page_size).limit(page_size)
    txs = await cursor.to_list(length=page_size)
    enriched = [await enrich_transaction(t, db) for t in txs]
    
    return {"total": total, "page": page, "page_size": page_size, "data": enriched}

@router.post("", status_code=201)
async def create_transaction(data: TransactionCreate, current_user=Depends(get_current_user)):
    db = get_db()
    doc = data.model_dump()
    doc["user_id"] = str(current_user["_id"])
    doc["created_at"] = datetime.utcnow()
    result = await db.transactions.insert_one(doc)
    doc["_id"] = result.inserted_id
    return await enrich_transaction(doc, db)

@router.put("/{tx_id}")
async def update_transaction(tx_id: str, data: TransactionUpdate, current_user=Depends(get_current_user)):
    db = get_db()
    tx = await db.transactions.find_one({"_id": ObjectId(tx_id), "user_id": str(current_user["_id"])})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if update:
        await db.transactions.update_one({"_id": ObjectId(tx_id)}, {"$set": update})
    updated = await db.transactions.find_one({"_id": ObjectId(tx_id)})
    return await enrich_transaction(updated, db)

@router.delete("/{tx_id}", status_code=204)
async def delete_transaction(tx_id: str, current_user=Depends(get_current_user)):
    db = get_db()
    result = await db.transactions.delete_one({"_id": ObjectId(tx_id), "user_id": str(current_user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
