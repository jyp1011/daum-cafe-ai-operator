from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.database import supabase
from app.api.deps import get_current_user
from app.services.moderation_service import analyze_content_item

router = APIRouter(tags=["moderation"])


class AnalyzeRequest(BaseModel):
    content_type: str = "POST"  # POST / COMMENT
    content_body: str
    content_title: Optional[str] = ""
    author_nickname: Optional[str] = ""
    content_url: Optional[str] = ""


class ActionRequest(BaseModel):
    action: str  # HIDDEN / DELETED / WARNED / IGNORED


class BulkActionRequest(BaseModel):
    item_ids: list[str]
    action: str


def _verify_cafe_access(cafe_id: str, operator_id: str):
    result = supabase.table("cafes").select("id").eq("id", cafe_id).eq("operator_id", operator_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Cafe not found")


@router.post("/cafes/{cafe_id}/moderation/analyze", status_code=201)
async def analyze(cafe_id: str, body: AnalyzeRequest, current_user: dict = Depends(get_current_user)):
    _verify_cafe_access(cafe_id, current_user["id"])
    return await analyze_content_item(
        cafe_id, body.content_type, body.content_body,
        body.content_title, body.author_nickname, body.content_url
    )


@router.get("/cafes/{cafe_id}/moderation/queue")
async def get_queue(cafe_id: str, threat_level: Optional[str] = None,
                    current_user: dict = Depends(get_current_user)):
    _verify_cafe_access(cafe_id, current_user["id"])
    query = supabase.table("moderation_items").select("*").eq("cafe_id", cafe_id).eq("status", "PENDING").order("created_at", desc=True)
    if threat_level:
        query = query.eq("threat_level", threat_level)
    return query.execute().data


@router.get("/cafes/{cafe_id}/moderation/stats")
async def get_stats(cafe_id: str, current_user: dict = Depends(get_current_user)):
    _verify_cafe_access(cafe_id, current_user["id"])
    all_items = supabase.table("moderation_items").select("threat_level, status, threat_categories, created_at").eq("cafe_id", cafe_id).execute().data

    total = len(all_items)
    by_level = {"CLEAN": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    actioned = 0
    for item in all_items:
        lvl = item.get("threat_level", "CLEAN")
        by_level[lvl] = by_level.get(lvl, 0) + 1
        if item.get("status") != "PENDING":
            actioned += 1

    return {
        "total_analyzed": total,
        "by_threat_level": by_level,
        "action_rate": round(actioned / total * 100, 1) if total > 0 else 0,
        "pending_count": total - actioned,
    }


@router.get("/cafes/{cafe_id}/moderation/{item_id}")
async def get_item(cafe_id: str, item_id: str, current_user: dict = Depends(get_current_user)):
    _verify_cafe_access(cafe_id, current_user["id"])
    result = supabase.table("moderation_items").select("*").eq("id", item_id).eq("cafe_id", cafe_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Item not found")
    return result.data


@router.patch("/cafes/{cafe_id}/moderation/{item_id}/action")
async def action_item(cafe_id: str, item_id: str, body: ActionRequest,
                      current_user: dict = Depends(get_current_user)):
    _verify_cafe_access(cafe_id, current_user["id"])
    status_map = {"HIDDEN": "ACTIONED", "DELETED": "ACTIONED", "WARNED": "ACTIONED", "IGNORED": "IGNORED"}
    result = supabase.table("moderation_items").update({
        "operator_action": body.action,
        "status": status_map.get(body.action, "ACTIONED"),
        "decided_by": current_user["id"],
    }).eq("id", item_id).eq("cafe_id", cafe_id).execute()
    return result.data[0] if result.data else {}


@router.post("/cafes/{cafe_id}/moderation/bulk-action")
async def bulk_action(cafe_id: str, body: BulkActionRequest, current_user: dict = Depends(get_current_user)):
    _verify_cafe_access(cafe_id, current_user["id"])
    status_map = {"HIDDEN": "ACTIONED", "DELETED": "ACTIONED", "WARNED": "ACTIONED", "IGNORED": "IGNORED"}
    for item_id in body.item_ids:
        supabase.table("moderation_items").update({
            "operator_action": body.action,
            "status": status_map.get(body.action, "ACTIONED"),
            "decided_by": current_user["id"],
        }).eq("id", item_id).eq("cafe_id", cafe_id).execute()
    return {"updated": len(body.item_ids)}


@router.get("/cafes/{cafe_id}/moderation/history")
async def get_history(cafe_id: str, current_user: dict = Depends(get_current_user)):
    _verify_cafe_access(cafe_id, current_user["id"])
    result = supabase.table("moderation_items").select("*").eq("cafe_id", cafe_id).neq("status", "PENDING").order("decided_at", desc=True).limit(50).execute()
    return result.data
