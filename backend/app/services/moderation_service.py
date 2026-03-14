import re
import asyncio
from difflib import SequenceMatcher
from app.database import supabase
from app.ai.claude_client import analyze_content


SPAM_PATTERNS = [
    r"(?:\d{2,4}[-\s]?\d{3,4}[-\s]?\d{4})",  # 전화번호
    r"(카톡|카카오톡|텔레그램|라인)\s*[:\s]\s*\w+",  # 메신저 ID
    r"(월\s*\d+만원|일당\s*\d+만원|재택\s*알바|부업|투잡)",  # 광고성 키워드
    r"(클릭|바로가기|지금 신청|무료 체험).{0,10}(http|www|\.com|\.kr)",  # CTA + 링크
]


def _rule_based_filter(content: str) -> dict:
    matched = []
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            matched.append(pattern)

    # 도배 탐지 (문장 반복)
    sentences = [s.strip() for s in content.split("\n") if len(s.strip()) > 5]
    if len(sentences) >= 3:
        for i in range(len(sentences) - 1):
            ratio = SequenceMatcher(None, sentences[i], sentences[i + 1]).ratio()
            if ratio > 0.8:
                matched.append("repeated_sentences")
                break

    return {"is_spam": len(matched) > 0, "matched_patterns": matched}


async def analyze_content_item(cafe_id: str, content_type: str, content_body: str,
                                content_title: str = "", author_nickname: str = "",
                                content_url: str = "") -> dict:
    # 카페 주제 조회
    cafe = supabase.table("cafes").select("topic").eq("id", cafe_id).single().execute()
    cafe_topic = cafe.data.get("topic", "일반") if cafe.data else "일반"

    # 1단계: 규칙 기반 필터
    rule_result = _rule_based_filter(content_body)

    # 2단계: Claude AI 분석
    ai_result = await asyncio.to_thread(analyze_content, content_body, content_title, cafe_topic)

    # 최종 위험도 결합 (규칙 기반이 HIGH 이상이면 유지)
    final_threat_level = ai_result.get("threat_level", "CLEAN")
    if rule_result["is_spam"] and final_threat_level in ("CLEAN", "LOW"):
        final_threat_level = "MEDIUM"
        ai_result["threat_categories"] = list(set(ai_result.get("threat_categories", []) + ["SPAM"]))
        ai_result["ai_reason"] = "패턴 기반 스팸 감지: " + ai_result.get("ai_reason", "")

    # 팬 문화 표현인 경우 위험도 완화
    if ai_result.get("is_fan_culture") and final_threat_level == "MEDIUM":
        final_threat_level = "LOW"

    ai_result["threat_level"] = final_threat_level

    # DB 저장
    result = supabase.table("moderation_items").insert({
        "cafe_id": cafe_id,
        "content_type": content_type,
        "content_url": content_url or None,
        "content_title": content_title or None,
        "content_body": content_body,
        "author_nickname": author_nickname or None,
        "threat_level": final_threat_level,
        "threat_score": ai_result.get("threat_score", 0.0),
        "threat_categories": ai_result.get("threat_categories", []),
        "ai_analysis": ai_result,
        "ai_recommendation": ai_result.get("ai_recommendation", "IGNORE"),
        "ai_reason": ai_result.get("ai_reason", ""),
        "status": "PENDING",
    }).execute()

    return result.data[0]
