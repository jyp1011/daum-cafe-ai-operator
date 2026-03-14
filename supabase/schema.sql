-- =============================================
-- 다음 카페 AI 운영자 - Supabase 스키마
-- Supabase SQL Editor에서 실행하세요
-- =============================================

-- 운영자 테이블 (Supabase auth.users와 연동)
CREATE TABLE IF NOT EXISTS operators (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email       TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 카페 테이블
CREATE TABLE IF NOT EXISTS cafes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operator_id     UUID NOT NULL REFERENCES operators(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    daum_cafe_url   TEXT NOT NULL,
    daum_cafe_id    TEXT NOT NULL,
    topic           TEXT NOT NULL,
    topic_keywords  TEXT[] DEFAULT '{}',
    description     TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 카페 설정 테이블
CREATE TABLE IF NOT EXISTS cafe_settings (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cafe_id                 UUID NOT NULL UNIQUE REFERENCES cafes(id) ON DELETE CASCADE,
    quiz_enabled            BOOLEAN DEFAULT TRUE,
    quiz_difficulty         TEXT DEFAULT 'MEDIUM',
    quiz_question_count     INT DEFAULT 5,
    quiz_pass_score         INT DEFAULT 80,
    quiz_auto_refresh_days  INT DEFAULT 7,
    moderation_enabled      BOOLEAN DEFAULT TRUE,
    moderation_sensitivity  TEXT DEFAULT 'MEDIUM',
    auto_hide_threshold     FLOAT DEFAULT 0.8,
    crawl_news              BOOLEAN DEFAULT TRUE,
    crawl_official_site     BOOLEAN DEFAULT FALSE,
    official_site_url       TEXT,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- 퀴즈 생성 태스크 테이블 (비동기 처리용)
CREATE TABLE IF NOT EXISTS quiz_generation_tasks (
    id              UUID PRIMARY KEY,
    cafe_id         UUID NOT NULL REFERENCES cafes(id) ON DELETE CASCADE,
    status          TEXT DEFAULT 'PENDING',  -- PENDING/CRAWLING/GENERATING/COMPLETED/FAILED
    quiz_set_id     UUID,
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 퀴즈 세트 테이블
CREATE TABLE IF NOT EXISTS quiz_sets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cafe_id         UUID NOT NULL REFERENCES cafes(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    status          TEXT DEFAULT 'DRAFT',  -- DRAFT/ACTIVE/ARCHIVED
    source_data     JSONB,
    generated_at    TIMESTAMPTZ DEFAULT NOW(),
    activated_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    created_by      TEXT DEFAULT 'AI',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 퀴즈 문항 테이블
CREATE TABLE IF NOT EXISTS quiz_questions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_set_id     UUID NOT NULL REFERENCES quiz_sets(id) ON DELETE CASCADE,
    order_num       INT NOT NULL,
    question_type   TEXT NOT NULL,  -- MULTIPLE_CHOICE/OX/SHORT_ANSWER
    question_text   TEXT NOT NULL,
    options         JSONB,
    correct_answer  TEXT NOT NULL,
    explanation     TEXT,
    source_url      TEXT,
    difficulty      TEXT DEFAULT 'MEDIUM',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 등업 신청 테이블
CREATE TABLE IF NOT EXISTS quiz_applications (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cafe_id             UUID NOT NULL REFERENCES cafes(id) ON DELETE CASCADE,
    quiz_set_id         UUID REFERENCES quiz_sets(id),
    applicant_nickname  TEXT NOT NULL,
    applicant_cafe_id   TEXT,
    submitted_content   TEXT NOT NULL,
    submission_method   TEXT DEFAULT 'MANUAL_INPUT',
    ai_score            INT,
    ai_grading_detail   JSONB,
    ai_recommendation   TEXT,  -- APPROVE/REJECT/MANUAL_REVIEW
    ai_reason           TEXT,
    status              TEXT DEFAULT 'PENDING',  -- PENDING/APPROVED/REJECTED/REVIEWING
    operator_decision   TEXT,
    operator_note       TEXT,
    decided_by          UUID REFERENCES operators(id),
    decided_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- 모더레이션 항목 테이블
CREATE TABLE IF NOT EXISTS moderation_items (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cafe_id             UUID NOT NULL REFERENCES cafes(id) ON DELETE CASCADE,
    content_type        TEXT NOT NULL,  -- POST/COMMENT
    content_url         TEXT,
    content_title       TEXT,
    content_body        TEXT NOT NULL,
    author_nickname     TEXT,
    posted_at           TIMESTAMPTZ,
    input_method        TEXT DEFAULT 'MANUAL',
    threat_level        TEXT,  -- CLEAN/LOW/MEDIUM/HIGH/CRITICAL
    threat_score        FLOAT,
    threat_categories   TEXT[],
    ai_analysis         JSONB,
    ai_recommendation   TEXT,  -- IGNORE/WARN/HIDE/DELETE
    ai_reason           TEXT,
    status              TEXT DEFAULT 'PENDING',  -- PENDING/ACTIONED/IGNORED/FALSE_POSITIVE
    operator_action     TEXT,  -- HIDDEN/DELETED/WARNED/IGNORED
    decided_by          UUID REFERENCES operators(id),
    decided_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- RLS (Row Level Security) 정책
-- =============================================

ALTER TABLE operators ENABLE ROW LEVEL SECURITY;
CREATE POLICY "operators_self" ON operators FOR ALL USING (auth.uid() = id);

ALTER TABLE cafes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "cafes_owner" ON cafes FOR ALL USING (operator_id = auth.uid());

ALTER TABLE cafe_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "cafe_settings_owner" ON cafe_settings FOR ALL
    USING (cafe_id IN (SELECT id FROM cafes WHERE operator_id = auth.uid()));

ALTER TABLE quiz_generation_tasks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tasks_owner" ON quiz_generation_tasks FOR ALL
    USING (cafe_id IN (SELECT id FROM cafes WHERE operator_id = auth.uid()));

ALTER TABLE quiz_sets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "quiz_sets_owner" ON quiz_sets FOR ALL
    USING (cafe_id IN (SELECT id FROM cafes WHERE operator_id = auth.uid()));

ALTER TABLE quiz_questions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "quiz_questions_owner" ON quiz_questions FOR ALL
    USING (quiz_set_id IN (SELECT id FROM quiz_sets WHERE cafe_id IN (SELECT id FROM cafes WHERE operator_id = auth.uid())));

ALTER TABLE quiz_applications ENABLE ROW LEVEL SECURITY;
CREATE POLICY "applications_owner" ON quiz_applications FOR ALL
    USING (cafe_id IN (SELECT id FROM cafes WHERE operator_id = auth.uid()));

ALTER TABLE moderation_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "moderation_owner" ON moderation_items FOR ALL
    USING (cafe_id IN (SELECT id FROM cafes WHERE operator_id = auth.uid()));
