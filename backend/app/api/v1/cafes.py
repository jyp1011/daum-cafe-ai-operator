from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.database import supabase
from app.api.deps import get_current_user

router = APIRouter(prefix="/cafes", tags=["cafes"])


class CafeCreate(BaseModel):
    name: str
    daum_cafe_url: str
    daum_cafe_id: str
    topic: str
    topic_keywords: list[str] = []
    description: Optional[str] = None


class CafeSettingsUpdate(BaseModel):
    quiz_enabled: Optional[bool] = None
    quiz_difficulty: Optional[str] = None
    quiz_question_count: Optional[int] = None
    quiz_pass_score: Optional[int] = None
    quiz_auto_refresh_days: Optional[int] = None
    moderation_enabled: Optional[bool] = None
    moderation_sensitivity: Optional[str] = None
    auto_hide_threshold: Optional[float] = None
    crawl_news: Optional[bool] = None
    crawl_official_site: Optional[bool] = None
    official_site_url: Optional[str] = None


@router.get("")
async def list_cafes(current_user: dict = Depends(get_current_user)):
    result = supabase.table("cafes").select("*").eq("operator_id", current_user["id"]).execute()
    return result.data


@router.post("", status_code=201)
async def create_cafe(body: CafeCreate, current_user: dict = Depends(get_current_user)):
    result = supabase.table("cafes").insert({
        **body.model_dump(),
        "operator_id": current_user["id"],
    }).execute()
    cafe = result.data[0]
    # 기본 설정 생성
    supabase.table("cafe_settings").insert({"cafe_id": cafe["id"]}).execute()
    return cafe


@router.get("/{cafe_id}")
async def get_cafe(cafe_id: str, current_user: dict = Depends(get_current_user)):
    result = supabase.table("cafes").select("*").eq("id", cafe_id).eq("operator_id", current_user["id"]).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Cafe not found")
    return result.data


@router.patch("/{cafe_id}")
async def update_cafe(cafe_id: str, body: dict, current_user: dict = Depends(get_current_user)):
    await get_cafe(cafe_id, current_user)
    result = supabase.table("cafes").update(body).eq("id", cafe_id).execute()
    return result.data[0]


@router.delete("/{cafe_id}", status_code=204)
async def delete_cafe(cafe_id: str, current_user: dict = Depends(get_current_user)):
    await get_cafe(cafe_id, current_user)
    supabase.table("cafes").delete().eq("id", cafe_id).execute()


@router.get("/{cafe_id}/settings")
async def get_settings(cafe_id: str, current_user: dict = Depends(get_current_user)):
    await get_cafe(cafe_id, current_user)
    result = supabase.table("cafe_settings").select("*").eq("cafe_id", cafe_id).single().execute()
    return result.data


@router.put("/{cafe_id}/settings")
async def update_settings(cafe_id: str, body: CafeSettingsUpdate, current_user: dict = Depends(get_current_user)):
    await get_cafe(cafe_id, current_user)
    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    result = supabase.table("cafe_settings").update(update_data).eq("cafe_id", cafe_id).execute()
    return result.data[0]
