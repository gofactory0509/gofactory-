# Go터뷰 V3 — 릴리스 노트 (WIP)

> 브랜치: `feature/v3-domain-specialization`
> 발표 일정에 맞춰 단계적 통합 진행 중. main 머지 전 BYOK·프론트엔드 트랙과 동기화 필요.

---

## 한눈에 보기

| 영역 | 변경 |
|---|---|
| 📚 **직무 카탈로그** | 4직무(반도체/백엔드/데이터/마케팅) → **삼성전자 DS부문 '26상 공채 직무기술서 기준 10직무** |
| 🏢 **사업부 단위 면접** | 같은 직무라도 메모리/Foundry/S.LSI/AI센터 등 사업부 선택 → 사업부 컨텍스트 AI 프롬프트 주입 |
| 🏭 **회사 정보 캐시** | 한국 주요 반도체 5개사(삼성전자/SK하이닉스/DB하이텍/한미반도체/솔브레인) 인재상·주력사업·트렌드 캐시 → AI 평가 정확도 향상 |
| 🎯 **약점 영역 집중 연습** | 5개 세부 점수(논리성/직무적합성/구체성/표현력/차별성)의 평균이 가장 낮은 영역 식별 → 그 역량을 집중 평가하는 맞춤 질문 생성 |
| 🎤 **음성 답변 입력** | 마이크 녹음 → Gemini 멀티모달 STT(BYOK·기존 키 재사용) → 답변란 자동 채움 |

---

## 1. 이번 세션에서 작업한 변경 (직무 카탈로그 + 회사 정보)

### 1-1. 직무 카탈로그 V3 (삼성 DS 직무기술서 기반)

**근거 자료**: 삼성전자 DS부문 2026년 상반기 3급 신입사원 채용 직무기술서 PDF (62쪽)

10개 직무 (경영지원·재무 제외):

```python
JOB_BUSINESS_UNITS = {
    "반도체공정기술":   ["메모리", "Foundry", "반도체연구소", "TSP총괄"],
    "설비기술":         ["메모리", "Foundry", "반도체연구소"],
    "회로설계":         ["S.LSI", "Foundry"],
    "신호및시스템설계":  ["S.LSI", "AI센터"],
    "평가및분석":       ["S.LSI", "Foundry"],
    "반도체공정설계":    ["S.LSI", "Foundry"],
    "생산관리":         ["Foundry", "TSP총괄"],
    "인프라기술":       ["글로벌 제조&인프라"],
    "환경":             ["글로벌 제조&인프라"],
    "SW개발":           ["AI센터"],
}
```

- `JOB_DESCRIPTIONS`: 직무별 1줄 설명 (UI 캡션)
- `SEED_QUESTIONS`: 10직무 × 7질문 = **70개** (난이도 하·중·상 분포)
- `interviews.business_unit` 컬럼 ALTER 마이그레이션
- AI 프롬프트에 사업부 컨텍스트(주력 제품·핵심 기술·최근 동향) 주입

**변경 파일**: `database.py`, `app.py`, `ai_client.py`

### 1-2. 회사 정보 캐시 시스템 (Phase 1 — 수동 시드)

`companies` 테이블 신설 + 5개 회사 수동 시드:

| 회사 | 산업 |
|---|---|
| 삼성전자 | 반도체-IDM (메모리·시스템·Foundry) |
| SK하이닉스 | 반도체-IDM (메모리, HBM 글로벌 1위) |
| DB하이텍 | 반도체-Foundry (8인치 특화) |
| 한미반도체 | 반도체-장비 (HBM TC Bonder) |
| 솔브레인 | 반도체-소재 (식각액·CMP·전구체) |

각 회사: `talent_profile`, `business_focus`, `recent_news_summary`, `recruiting_status`, `source_urls`

**DB 메서드 추가**:
- `get_company_info(query)` — 이름·별칭(`aliases`) 통합 검색, 캐시 미스 시 None
- `upsert_company_info(info)` — 신규 삽입/갱신 (Phase 2 크롤러 결과 저장용)
- `list_cached_companies()` — UI 자동완성용 목록

**AI 통합**:
- `generate_question(..., company_info=None)` — 캐시 회사 정보를 프롬프트에 주입
- `evaluate_answer(..., company_info=None)` — 평가 시 회사 인재상·주력사업 적합성 반영

**UI 변경 (사이드바)**:
- 자유 텍스트 입력 → **검색 가능한 드롭다운** + "기타 (직접 입력)" 옵션
- 캐시 적중 시 산업 분류 캡션 표시
- "💡 회사 정보가 면접 컨텍스트에 자동 반영됩니다" 안내

---

## 2. 다른 세션에서 통합된 변경

### 2-1. 🎯 약점 영역 집중 연습

5개 세부 점수(논리성/직무적합성/구체성/표현력/차별성)의 평균이 가장 낮은 영역을 식별해 그 역량을 집중 평가하는 맞춤 질문을 생성.

**핵심 동작**:
1. `interviews.{logic,fit,detail,expression,uniqueness}_score` 컬럼에서 최근 20건 집계
2. 평균이 가장 낮은 항목 식별 (예: "구체성")
3. `ai_client.generate_targeted_question(job_field, weakness=...)` 호출
4. 약점 영역을 강하게 자극하는 질문 생성 후 면접 플로우 진입

**필요 데이터**: 최소 3건 이상 세부 점수 누적 필요

### 2-2. 🎤 음성 답변 입력 (STT)

마이크 녹음 → Gemini 멀티모달 STT → 답변란 자동 채움.

**동작 흐름**:
1. `streamlit_mic_recorder.mic_recorder` 컴포넌트로 WAV 녹음
2. `ai_client.transcribe_audio(audio_bytes, mime_type="audio/wav")` 호출
3. Gemini 멀티모달에 한국어 받아쓰기 프롬프트 전달
4. 전사 결과를 `st.session_state["transcribed_answer"]` 로 저장 → 답변 textarea에 자동 채움

**의존성**: `streamlit-mic-recorder` (requirements.txt 추가)
**키 정책**: 기존 Gemini 키 재사용 (BYOK 통합 시 자동 적용)

---

## 3. BYOK · 프론트엔드 통합 포인트 (다른 트랙)

> 아래 영역은 **별도 트랙(다른 개발자)**이 작업 중이라 이 브랜치에서 변경하지 않았습니다.
> V3 변경사항을 가져갈 때 참고할 수 있도록 통합 지점만 명시합니다.

### 3-1. BYOK (Bring Your Own Key) — 비워둠

- **건드리지 않은 위치**:
  - `backend/config.py` (settings 기반 키 관리)
  - `backend/services/ai_client.py` (FastAPI용 AIService)
- **V3 측 영향 없음**: 루트 `ai_client.py`는 `AIClient(gemini_key=..., groq_key=...)` 직접 주입 방식 유지 (기존 Streamlit 측)
- **음성 입력**: 기존 Gemini 키를 그대로 재사용하므로 BYOK 통합 시 자동 흡수

### 3-2. 프론트엔드 (React+FastAPI 변환) — 통합 가이드

루트 `database.py`의 V3 데이터 구조는 **FastAPI 측에도 그대로 import 가능**합니다. backend 측에서 즉시 활용할 수 있도록 다음 상수를 정리해뒀습니다:

| 상수/메서드 | 위치 | FastAPI에서 사용 |
|---|---|---|
| `JOB_BUSINESS_UNITS` | database.py | `GET /api/jobs` 응답 데이터 |
| `JOB_DESCRIPTIONS` | database.py | 직무 카드 UI 캡션 |
| `SEED_QUESTIONS` | database.py | `common_questions` 시드 (앱 첫 실행 시 자동 삽입) |
| `COMPANY_SEEDS` | database.py | `companies` 시드 (앱 첫 실행 시 자동 삽입) |
| `InterviewDB.get_company_info(name)` | database.py | `GET /api/companies/{name}` 구현 |
| `InterviewDB.list_cached_companies()` | database.py | `GET /api/companies` (자동완성) |
| `InterviewDB.upsert_company_info(info)` | database.py | Phase 2 크롤러 결과 저장 |

**제안 엔드포인트 (구현 미정)**:
```
GET  /api/jobs                            → JOB_FIELDS + JOB_BUSINESS_UNITS + JOB_DESCRIPTIONS
GET  /api/companies                       → list_cached_companies()
GET  /api/companies/{name}                → get_company_info(name) (캐시 hit/miss)
POST /api/interview/start                 → job_field + business_unit + company + 자동 company_info 주입
POST /api/interview/answer                → ai_client.evaluate_answer(...) + company_info
```

`backend/services/database.py`, `backend/services/ai_client.py`는 변경하지 않았으므로 다른 개발자가 위 가이드에 따라 통합하면 됩니다.

---

## 4. 데이터 마이그레이션

기존 `interviews.db`에 대해:

| 테이블 | 변경 |
|---|---|
| `interviews` | 기존 기록 보존 + `business_unit`, `logic/fit/detail/expression/uniqueness_score` 컬럼 추가 |
| `common_questions` | 옛 4직무 28개 시드 자동 삭제 + 신규 10직무 70개 시드 삽입 |
| `companies` | 신규 테이블 생성 + 5개 회사 시드 |
| `question_bank`, `resumes`, `user_feedback` | 변경 없음 |

마이그레이션은 `database.py` 의 `_create_tables()` + `_seed_*()` 메서드가 자동 수행 — 앱 첫 실행 시 한 번만 동작.

---

## 5. 다음 단계 (V3 → V4)

### Phase 2 (다음 주)
- 회사 정보 크롤러 PoC: **삼성전자**부터
  - 네이버 뉴스 API (최근 7일)
  - DART OpenAPI (공시 요약)
  - 회사 채용 페이지 인재상 스크래핑
- `upsert_company_info()` 로 자동 갱신

### Phase 3 (3주차)
- AWS Batch + RDS 배포
  - EventBridge cron: 매주 일요일 02:00 KST
  - Fargate Spot 컨테이너로 크롤러 주기 실행
  - S3 raw 데이터 → Lambda LLM 요약 → RDS upsert

### Phase 4 (발표 직전)
- 캐시 회사 5개 → 20개 확장
- 통합 시연 시나리오 준비
- BYOK · React 프론트엔드와 최종 머지

---

## 6. 검증

이 브랜치를 로컬에서 실행하려면:

```powershell
pip install -r requirements.txt
streamlit run app.py
```

확인 포인트:
- 사이드바 직무 드롭다운에 **10개 반도체 직무**
- "회로설계" 선택 시 **사업부 라디오 (S.LSI/Foundry)**
- 회사 드롭다운에서 **검색**(타이핑 필터링) + 캐시 적중 표시
- 면접 시작 → AI 질문이 사업부·회사 특성 반영
- 기록 페이지에 사업부 표시
- 약점 영역 집중 연습 (3건 이상 평가 데이터 누적 후)
- 🎤 음성 답변 입력

---

## 출처

- 삼성전자 DS부문 2026년 상반기 3급 신입사원 채용 직무기술서 (PDF 62쪽)
- 채용 페이지: https://www.samsung-dsrecruit.com/
- 직무 분류: 메모리 / S.LSI / Foundry / CTO_반도체연구소 / 글로벌 제조&인프라 / TSP총괄 / AI센터
