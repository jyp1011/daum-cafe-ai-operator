from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4
from app.database import supabase
from app.api.deps import get_current_user
from app.services import quiz_service

router = APIRouter(tags=["quiz"])


class QuizGenerateRequest(BaseModel):
    topic_keywords: list[str] = []
    difficulty: str = "MEDIUM"
    question_count: int = 5
    extra_instructions: str = ""


class ApplicationCreate(BaseModel):
    applicant_nickname: str
    submitted_content: str
    quiz_set_id: str


class DecideRequest(BaseModel):
    decision: str  # APPROVED / REJECTED
    note: Optional[str] = None


def _verify_cafe_access(cafe_id: str, operator_id: str):
    result = supabase.table("cafes").select("id").eq("id", cafe_id).eq("operator_id", operator_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Cafe not found")


# ─── 퀴즈 생성 ───────────────────────────────────────────────────────────────

@router.post("/cafes/{cafe_id}/quiz/generate")
async def generate_quiz(cafe_id: str, body: QuizGenerateRequest, background_tasks: BackgroundTasks,
                        current_user: dict = Depends(get_current_user)):
    _verify_cafe_access(cafe_id, current_user["id"])

    cafe = supabase.table("cafes").select("topic, topic_keywords").eq("id", cafe_id).single().execute().data
    keywords = body.topic_keywords or cafe.get("topic_keywords") or [cafe["topic"]]

    task_id = str(uuid4())
    supabase.table("quiz_generation_tasks").insert({"id": task_id, "cafe_id": cafe_id, "status": "PENDING"}).execute()

    background_tasks.add_task(
        quiz_service.run_generation_pipeline,
        task_id, cafe_id, cafe["topic"], keywords,
        body.difficulty, body.question_count, body.extra_instructions
    )
    return {"task_id": task_id}


@router.get("/cafes/{cafe_id}/quiz/generate/{task_id}")
async def get_generation_status(cafe_id: str, task_id: str, current_user: dict = Depends(get_current_user)):
    _verify_cafe_access(cafe_id, current_user["id"])
    result = supabase.table("quiz_generation_tasks").select("*").eq("id", task_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Task not found")
    return result.data


# ─── 퀴즈 세트 관리 ──────────────────────────────────────────────────────────

@router.get("/cafes/{cafe_id}/quiz/sets")
async def list_quiz_sets(cafe_id: str, current_user: dict = Depends(get_current_user)):
    _verify_cafe_access(cafe_id, current_user["id"])
    result = supabase.table("quiz_sets").select("*").eq("cafe_id", cafe_id).order("created_at", desc=True).execute()
    return result.data


@router.get("/cafes/{cafe_id}/quiz/sets/{set_id}")
async def get_quiz_set(cafe_id: str, set_id: str, current_user: dict = Depends(get_current_user)):
    _verify_cafe_access(cafe_id, current_user["id"])
    quiz_set = supabase.table("quiz_sets").select("*").eq("id", set_id).eq("cafe_id", cafe_id).single().execute().data
    if not quiz_set:
        raise HTTPException(status_code=404, detail="Quiz set not found")
    questions = supabase.table("quiz_questions").select("*").eq("quiz_set_id", set_id).order("order_num").execute().data
    return {**quiz_set, "questions": questions}


@router.patch("/cafes/{cafe_id}/quiz/sets/{set_id}")
async def update_quiz_set(cafe_id: str, set_id: str, body: dict, current_user: dict = Depends(get_current_user)):
    _verify_cafe_access(cafe_id, current_user["id"])
    allowed = {k: v for k, v in body.items() if k in ("status", "title")}
    result = supabase.table("quiz_sets").update(allowed).eq("id", set_id).eq("cafe_id", cafe_id).execute()
    return result.data[0] if result.data else {}


@router.patch("/quiz/questions/{question_id}")
async def update_question(question_id: str, body: dict, current_user: dict = Depends(get_current_user)):
    allowed_fields = ("question_text", "options", "correct_answer", "explanation", "source_url")
    update_data = {k: v for k, v in body.items() if k in allowed_fields}
    result = supabase.table("quiz_questions").update(update_data).eq("id", question_id).execute()
    return result.data[0] if result.data else {}


# ─── 등업 신청 ────────────────────────────────────────────────────────────────

@router.post("/cafes/{cafe_id}/applications", status_code=201)
async def create_application(cafe_id: str, body: ApplicationCreate, current_user: dict = Depends(get_current_user)):
    _verify_cafe_access(cafe_id, current_user["id"])
    from app.services.application_service import grade_application
    return await grade_application(cafe_id, body.quiz_set_id, body.applicant_nickname, body.submitted_content)


@router.get("/cafes/{cafe_id}/applications")
async def list_applications(cafe_id: str, status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    _verify_cafe_access(cafe_id, current_user["id"])
    query = supabase.table("quiz_applications").select("*").eq("cafe_id", cafe_id).order("created_at", desc=True)
    if status:
        query = query.eq("status", status)
    return query.execute().data


@router.get("/cafes/{cafe_id}/applications/{app_id}")
async def get_application(cafe_id: str, app_id: str, current_user: dict = Depends(get_current_user)):
    _verify_cafe_access(cafe_id, current_user["id"])
    result = supabase.table("quiz_applications").select("*").eq("id", app_id).eq("cafe_id", cafe_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Application not found")
    return result.data


@router.patch("/cafes/{cafe_id}/applications/{app_id}/decide")
async def decide_application(cafe_id: str, app_id: str, body: DecideRequest,
                              current_user: dict = Depends(get_current_user)):
    _verify_cafe_access(cafe_id, current_user["id"])
    result = supabase.table("quiz_applications").update({
        "status": body.decision,
        "operator_decision": body.decision,
        "operator_note": body.note,
        "decided_by": current_user["id"],
    }).eq("id", app_id).eq("cafe_id", cafe_id).execute()
    return result.data[0] if result.data else {}
