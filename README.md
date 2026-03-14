# 다음 카페 AI 운영자

다음(Daum) 카페 운영자를 위한 AI 자동화 웹서비스입니다.

## 주요 기능

- **AI 등업 퀴즈 자동 생성**: 최신 뉴스를 크롤링하여 카페 주제에 맞는 퀴즈를 자동 생성
- **등업 신청 자동 채점**: 신청 텍스트를 붙여넣으면 AI가 자동으로 채점하고 승인/반려 권고
- **콘텐츠 모더레이션**: 스팸·유해글을 AI가 분석하여 위험도 판정 및 처리 권고

## 기술 스택

- **Frontend**: Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: Python FastAPI
- **Database**: Supabase (PostgreSQL)
- **AI**: Anthropic Claude API

## 시작하기

### 1. Supabase 설정
1. [supabase.com](https://supabase.com)에서 새 프로젝트 생성
2. `supabase/schema.sql` 내용을 SQL Editor에서 실행

### 2. 백엔드 실행
```bash
cd backend
cp .env.example .env   # 환경변수 입력
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 3. 프론트엔드 실행
```bash
cd frontend
cp .env.local.example .env.local   # API URL 입력
npm install
npm run dev
```

### 4. 접속
- 프론트엔드: http://localhost:3000
- API 문서: http://localhost:8000/docs

## 환경변수

### 백엔드 (`backend/.env`)
| 변수 | 설명 |
|------|------|
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_ANON_KEY` | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |
| `SUPABASE_JWT_SECRET` | Supabase JWT secret (Settings > API) |
| `ANTHROPIC_API_KEY` | Anthropic API key |

### 프론트엔드 (`frontend/.env.local`)
| 변수 | 설명 |
|------|------|
| `NEXT_PUBLIC_API_URL` | 백엔드 API URL (기본: http://localhost:8000/api/v1) |
