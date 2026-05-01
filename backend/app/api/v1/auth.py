from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from app.database import supabase
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    try:
        result = supabase.auth.sign_up({"email": body.email, "password": body.password})
        if not result.user:
            raise HTTPException(status_code=400, detail="Registration failed")
        # 이메일 인증 없이 즉시 사용 가능하도록 자동 확인 처리
        supabase.auth.admin.update_user_by_id(result.user.id, {"email_confirm": True})
        supabase.table("operators").insert({
            "id": result.user.id,
            "email": body.email,
            "name": body.name,
        }).execute()
        return {"message": "Registration successful."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(body: LoginRequest):
    try:
        result = supabase.auth.sign_in_with_password({"email": body.email, "password": body.password})
        if not result.session:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {
            "access_token": result.session.access_token,
            "refresh_token": result.session.refresh_token,
            "token_type": "bearer",
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user
