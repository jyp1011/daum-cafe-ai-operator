import asyncio
from uuid import uuid4
from app.database import supabase
from app.crawlers.news_crawler import gather_context_for_quiz
from app.ai.claude_client import generate_quiz_from_context


async def run_generation_pipeline(task_id: str, cafe_id: str, topic: str, keywords: list,
                                  difficulty: str, question_count: int, extra_instructions: str):
    try:
        # 진행 상태 업데이트
        _update_task(task_id, "CRAWLING")

        context = await gather_context_for_quiz(keywords or [topic])

        _update_task(task_id, "GENERATING")

        result = await asyncio.to_thread(
            generate_quiz_from_context,
            topic, context, question_count, difficulty, extra_instructions
        )

        # 퀴즈 세트 저장
        quiz_set = supabase.table("quiz_sets").insert({
            "cafe_id": cafe_id,
            "title": f"AI 생성 퀴즈 - {topic}",
            "status": "DRAFT",
            "source_data": {"context_summary": context[:500]},
        }).execute().data[0]

        questions = result.get("questions", [])
        for q in questions:
            supabase.table("quiz_questions").insert({
                "quiz_set_id": quiz_set["id"],
                "order_num": q["order_num"],
                "question_type": q["question_type"],
                "question_text": q["question_text"],
                "options": q.get("options"),
                "correct_answer": q["correct_answer"],
                "explanation": q.get("explanation"),
                "source_url": q.get("source_url"),
                "difficulty": difficulty,
            }).execute()

        _update_task(task_id, "COMPLETED", quiz_set_id=quiz_set["id"])

    except Exception as e:
        _update_task(task_id, "FAILED", error=str(e))


def _update_task(task_id: str, status: str, quiz_set_id: str = None, error: str = None):
    data = {"status": status}
    if quiz_set_id:
        data["quiz_set_id"] = quiz_set_id
    if error:
        data["error_message"] = error
    supabase.table("quiz_generation_tasks").update(data).eq("id", task_id).execute()
