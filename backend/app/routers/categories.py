from fastapi import APIRouter, Depends, HTTPException
from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.schemas import CategoryCreate
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/api/categories", tags=["categories"])

def cat_to_out(cat: dict) -> dict:
    return {
        "id": str(cat["_id"]),
        "name": cat["name"],
        "type": cat["type"],
        "icon": cat.get("icon", "tag"),
        "is_default": cat.get("is_default", False),
    }

@router.get("")
async def list_categories(current_user=Depends(get_current_user)):
    db = get_db()
    user_id = str(current_user["_id"])
    cats = await db.categories.find({"user_id": user_id}).to_list(length=200)
    return [cat_to_out(c) for c in cats]

@router.post("", status_code=201)
async def create_category(data: CategoryCreate, current_user=Depends(get_current_user)):
    db = get_db()
    doc = data.model_dump()
    doc["user_id"] = str(current_user["_id"])
    doc["is_default"] = False
    doc["created_at"] = datetime.utcnow()
    result = await db.categories.insert_one(doc)
    doc["_id"] = result.inserted_id
    return cat_to_out(doc)

@router.delete("/{cat_id}", status_code=204)
async def delete_category(cat_id: str, current_user=Depends(get_current_user)):
    db = get_db()
    cat = await db.categories.find_one({"_id": ObjectId(cat_id), "user_id": str(current_user["_id"])})
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    if cat.get("is_default"):
        raise HTTPException(status_code=400, detail="Cannot delete default categories")
    await db.categories.delete_one({"_id": ObjectId(cat_id)})
