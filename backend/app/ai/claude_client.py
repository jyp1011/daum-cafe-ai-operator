import json
from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings

client = Anthropic(api_key=settings.anthropic_api_key)
MODEL = "claude-opus-4-6"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def generate_quiz_from_context(topic: str, context_text: str, question_count: int, difficulty: str, extra_instructions: str = "") -> dict:
    difficulty_map = {"EASY": "쉬움 (팬이라면 쉽게 알 수 있는 기본 정보)", "MEDIUM": "보통 (최근 활동을 잘 알고 있는 팬)", "HARD": "어려움 (열혈 팬만 알 수 있는 세부 정보)"}
    diff_desc = difficulty_map.get(difficulty, "보통")

    mc = max(1, question_count - 2)
    ox = 1
    sa = question_count - mc - ox

    prompt = f"""카페 주제: {topic}
최신 정보 (최근 수집된 뉴스/공지):
{context_text}

요구사항:
- 총 문항 수: {question_count}개
- 난이도: {diff_desc}
- 문제 유형: 객관식(4지선다) {mc}개, OX {ox}개, 단답형 {sa}개
- 주어진 최신 정보를 바탕으로 출제 (추측 금지)
- 각 문항에 출처 URL 포함
{f"- 추가 지시사항: {extra_instructions}" if extra_instructions else ""}

다음 JSON 형식으로만 반환해주세요 (다른 텍스트 없이):
{{
  "questions": [
    {{
      "order_num": 1,
      "question_type": "MULTIPLE_CHOICE",
      "question_text": "...",
      "options": ["① ...", "② ...", "③ ...", "④ ..."],
      "correct_answer": "① ...",
      "explanation": "...",
      "source_url": "https://..."
    }}
  ]
}}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system="당신은 한국 팬 커뮤니티 카페의 등업 퀴즈를 출제하는 전문가입니다. 주어진 최신 정보를 바탕으로 실제 팬이라면 알 수 있는 적절한 난이도의 퀴즈를 생성합니다. 반드시 JSON 형식으로만 응답합니다.",
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(response.content[0].text)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def parse_answer_submission(submitted_text: str, question_count: int) -> dict:
    prompt = f"""다음 등업 신청 텍스트에서 각 문항의 답을 추출해주세요.
문항 수: {question_count}개

신청 텍스트:
{submitted_text}

다음 JSON 형식으로만 반환해주세요:
{{"answers": {{"1": "답변내용", "2": "답변내용", ...}}}}

답변을 찾을 수 없는 문항은 null로 처리하세요."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system="주어진 텍스트에서 퀴즈 답변을 추출합니다. JSON 형식으로만 응답합니다.",
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(response.content[0].text)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def check_short_answer(correct: str, submitted: str) -> bool:
    prompt = f"""정답: "{correct}"
제출된 답변: "{submitted}"

이 두 답변이 같은 의미인지 판단해주세요. 동의어, 약어, 영문/한글 표기 차이도 허용합니다.
true 또는 false 중 하나만 반환하세요."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=10,
        system="퀴즈 답변의 의미적 동등성을 판단합니다. true 또는 false만 반환합니다.",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip().lower() == "true"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def analyze_content(content_body: str, content_title: str, cafe_topic: str) -> dict:
    prompt = f"""다음 게시글을 분석해주세요.

제목: {content_title or "(없음)"}
내용: {content_body}

다음 JSON 형식으로만 반환하세요:
{{
  "threat_level": "CLEAN|LOW|MEDIUM|HIGH|CRITICAL",
  "threat_score": 0.0,
  "threat_categories": [],
  "ai_recommendation": "IGNORE|WARN|HIDE|DELETE",
  "ai_reason": "판단 근거 (2-3문장)",
  "is_fan_culture": true
}}

threat_categories 선택지: SPAM(광고/홍보), HATE_SPEECH(혐오/비하), ADULT(성인/음란), PHISHING(사기/피싱), OFF_TOPIC(주제 무관), VIOLENCE(폭력)"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=f"""당신은 한국 온라인 팬 커뮤니티의 콘텐츠 모더레이터입니다.
카페 주제: {cafe_topic}

중요한 판단 기준:
- "완전 미쳤다", "죽겠다", "실신", "심장 멎는다" 등은 팬덤 과장 표현 → CLEAN
- 아티스트 칭찬 표현은 CLEAN
- 타 팬덤/아티스트 비하 → HATE_SPEECH
- 광고성 링크/전화번호 포함 → SPAM
- 개인정보 노출 → HIGH
팬덤 문화 표현을 스팸/혐오로 오탐하지 않도록 주의하세요. JSON 형식으로만 응답합니다.""",
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(response.content[0].text)
