import asyncio
from app.database import supabase
from app.ai.claude_client import parse_answer_submission, check_short_answer


async def grade_application(cafe_id: str, quiz_set_id: str, applicant_nickname: str, submitted_content: str) -> dict:
    # 퀴즈 문항 조회
    questions_result = supabase.table("quiz_questions").select("*").eq("quiz_set_id", quiz_set_id).order("order_num").execute()
    questions = questions_result.data
    if not questions:
        raise ValueError("No questions found for this quiz set")

    # 답변 파싱
    parsed = await asyncio.to_thread(parse_answer_submission, submitted_content, len(questions))
    submitted_answers = parsed.get("answers", {})

    # 채점
    grading_detail = {}
    correct_count = 0

    for q in questions:
        num = str(q["order_num"])
        submitted = submitted_answers.get(num)
        correct = q["correct_answer"]
        is_correct = False

        if submitted is None:
            is_correct = False
        elif q["question_type"] in ("MULTIPLE_CHOICE", "OX"):
            is_correct = submitted.strip().lower() == correct.strip().lower()
        else:  # SHORT_ANSWER
            is_correct = await asyncio.to_thread(check_short_answer, correct, submitted)

        if is_correct:
            correct_count += 1

        grading_detail[num] = {
            "question": q["question_text"],
            "submitted": submitted,
            "correct_answer": correct,
            "is_correct": is_correct,
        }

    total = len(questions)
    score = int((correct_count / total) * 100) if total > 0 else 0

    # 합격 기준 조회
    settings_result = supabase.table("cafe_settings").select("quiz_pass_score").eq("cafe_id", cafe_id).single().execute()
    pass_score = settings_result.data.get("quiz_pass_score", 80) if settings_result.data else 80

    if score >= pass_score:
        recommendation = "APPROVE"
        reason = f"{total}문항 중 {correct_count}문항 정답 ({score}점), 합격 기준 {pass_score}점 충족"
    elif score >= pass_score - 20:
        recommendation = "MANUAL_REVIEW"
        reason = f"{total}문항 중 {correct_count}문항 정답 ({score}점), 합격 기준 {pass_score}점에 근접 — 운영진 검토 권고"
    else:
        recommendation = "REJECT"
        reason = f"{total}문항 중 {correct_count}문항 정답 ({score}점), 합격 기준 {pass_score}점 미달"

    # DB 저장
    result = supabase.table("quiz_applications").insert({
        "cafe_id": cafe_id,
        "quiz_set_id": quiz_set_id,
        "applicant_nickname": applicant_nickname,
        "submitted_content": submitted_content,
        "ai_score": score,
        "ai_grading_detail": grading_detail,
        "ai_recommendation": recommendation,
        "ai_reason": reason,
        "status": "PENDING",
    }).execute()

    return result.data[0]
