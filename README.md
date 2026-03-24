# Partners Bot AI Hub

운영 허브용 AI 보조 기능(인박스 파싱, 항목 분석, 룰 초안, 대시보드 브리핑, 프롬프트 관리)을 포함한 React + Vite + Express 프로젝트입니다.

## 1) 환경 변수 설정

```bash
cp .env.example .env
cp server/.env.example server/.env
```

필수:
- `GEMINI_API_KEY`: Gemini API 키

권장:
- `GEMINI_MODEL` (기본값: `gemini-2.0-flash`)
- `PORT` (기본값: `3000`)
- `DB_PATH` (기본값: `./server/app.db`)

## 2) 설치

```bash
npm install
```

## 3) DB 초기화

별도 명령이 필요하지 않습니다. 백엔드 시작 시 `initDb()`가 idempotent하게 테이블/컬럼/시드 프롬프트를 자동 보장합니다.

## 4) 실행

백엔드:
```bash
npm run dev:server
```

프론트엔드:
```bash
npm run dev
```

프론트 서버는 `0.0.0.0:5173`에서 실행되며 기본적으로 `/api`를 `http://localhost:3000`으로 프록시합니다.

배포 빌드 미리보기:
```bash
npm run build
npm run preview
```
(미리보기는 `0.0.0.0:4173`)

## 5) 주요 엔드포인트

- `POST /api/ai/inbox-parse`
- `POST /api/ai/analyze-item`
- `POST /api/ai/rule-draft`
- `GET /api/ai/dashboard-briefing`
- `GET /api/prompt-profiles`
- `PUT /api/prompt-profiles/:promptKey`
- `POST /api/automation/rules`

## 6) 확인 포인트

- 성공한 AI 호출은 `ai_runs`에 저장됩니다.
- 위험도 있는 룰은 자동 활성화되지 않고 `proposed`로 저장됩니다.
- 프롬프트 프로필은 DB에서 로드/수정 가능합니다.
