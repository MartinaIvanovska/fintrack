from fastapi import APIRouter, HTTPException, status, Depends
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token, get_current_user
from app.schemas.schemas import UserRegister, TokenResponse, UserOut, UserUpdate, PasswordChange
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/api/auth", tags=["auth"])

def user_to_out(user: dict) -> UserOut:
    return UserOut(
        id=str(user["_id"]),
        username=user["username"],
        email=user["email"],
        created_at=user.get("created_at", datetime.utcnow())
    )

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: UserRegister, db=Depends(get_db)):
    print(repr(data.password))
    print(len(data.password))
    if await db.users.find_one({"email": data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await db.users.find_one({"username": data.username}):
        raise HTTPException(status_code=400, detail="Username already taken")
    
    user_doc = {
        "username": data.username,
        "email": data.email,
        "hashed_password": get_password_hash(data.password),
        "created_at": datetime.utcnow()
    }
    result = await db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    
    # Seed default categories for the user
    await seed_default_categories(db, str(result.inserted_id))
    
    token = create_access_token({"sub": str(result.inserted_id)})
    return TokenResponse(access_token=token, user=user_to_out(user_doc))

@router.post("/login", response_model=TokenResponse)
async def login(data: UserRegister, db=Depends(get_db)):
    user = await db.users.find_one({"email": data.email})
    if not user or not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"sub": str(user["_id"])})
    return TokenResponse(access_token=token, user=user_to_out(user))

@router.get("/me", response_model=UserOut)
async def get_me(current_user=Depends(get_current_user)):
    return user_to_out(current_user)

@router.put("/me", response_model=UserOut)
async def update_profile(data: UserUpdate, current_user=Depends(get_current_user)):
    db = get_db()
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if update:
        await db.users.update_one({"_id": current_user["_id"]}, {"$set": update})
    updated = await db.users.find_one({"_id": current_user["_id"]})
    return user_to_out(updated)

@router.post("/change-password")
async def change_password(data: PasswordChange, current_user=Depends(get_current_user)):
    db = get_db()
    if not verify_password(data.current_password, current_user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    new_hash = get_password_hash(data.new_password)
    await db.users.update_one({"_id": current_user["_id"]}, {"$set": {"hashed_password": new_hash}})
    return {"message": "Password updated successfully"}

async def seed_default_categories(db, user_id: str):
    defaults = [
        {"name": "Salary", "type": "income", "icon": "briefcase"},
        {"name": "Freelance", "type": "income", "icon": "laptop"},
        {"name": "Investment", "type": "income", "icon": "trending-up"},
        {"name": "Other Income", "type": "income", "icon": "plus-circle"},
        {"name": "Food & Dining", "type": "expense", "icon": "utensils"},
        {"name": "Housing", "type": "expense", "icon": "home"},
        {"name": "Transport", "type": "expense", "icon": "car"},
        {"name": "Healthcare", "type": "expense", "icon": "heart"},
        {"name": "Entertainment", "type": "expense", "icon": "film"},
        {"name": "Shopping", "type": "expense", "icon": "shopping-bag"},
        {"name": "Utilities", "type": "expense", "icon": "zap"},
        {"name": "Subscriptions", "type": "expense", "icon": "refresh-cw"},
        {"name": "Education", "type": "expense", "icon": "book"},
        {"name": "Other", "type": "expense", "icon": "tag"},
    ]
    for cat in defaults:
        cat["user_id"] = user_id
        cat["is_default"] = True
        await db.categories.insert_one(cat)
