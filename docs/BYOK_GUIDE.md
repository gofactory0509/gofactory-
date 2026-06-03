# Go터뷰 BYOK (Bring Your Own Key) 가이드

이 문서는 Go터뷰의 **BYOK 시스템** 동작 원리·사용법·운영 시 고려사항을
설명합니다. 일반 사용자(End-user)와 개발자(Maintainer) 양쪽을 대상으로 합니다.

---

## 1. 한눈에 보기

| 항목 | 기본 (키 없음) | BYOK (사용자 키 있음) |
|---|---|---|
| LLM 백엔드 | AWS Bedrock (Claude Sonnet 4.6) | OpenRouter (사용자 선택) |
| 비용 부담 | 서비스 운영자 (AWS 학생 크레딧) | 사용자 본인 |
| 모델 선택 | 고정 (Claude Sonnet 4.6) | GPT-4o / Claude / Gemini 등 |
| 자유도 | 낮음 | 높음 |
| 키 저장 | 해당 없음 | 서버 미저장, 브라우저 옵션 |

**핵심 원칙:** 사용자가 키를 입력하지 않아도 서비스를 100% 사용 가능합니다. 키 입력은 "더 빠른/저렴한/원하는 모델을 쓰고 싶을 때"의 선택지입니다.

---

## 2. 사용자 가이드

### 2.1 OpenRouter 키 발급

1. [https://openrouter.ai/keys](https://openrouter.ai/keys) 접속 → 로그인
2. `Create Key` 클릭 → 라벨 입력 (예: "gofactory")
3. `sk-or-v1-...` 로 시작하는 키를 복사

### 2.2 Go터뷰에서 키 사용

**웹 UI (FastAPI):**

1. 상단 네비게이션 아래 `🔑 API 키 설정 (선택)` 펼치기
2. 발급받은 키를 붙여넣기
3. 모델 드롭다운에서 원하는 모델 선택 (기본: Claude Sonnet 4.6)
4. `키 검증` 클릭 → ✅ 표시 확인
5. 이후 모든 면접 질문 생성·답변 평가가 본인 키로 호출됨
6. 상단 배지가 `🔑 OpenRouter` 로 바뀜

**Streamlit UI (`app.py`):**

1. 좌측 사이드바 `🔑 OpenRouter API 키 (선택)` 펼치기
2. 키 붙여넣기 → 모델 선택 → `키 검증` 버튼
3. 사이드바 하단 "📍 현재 백엔드: 🔑 OpenRouter" 확인

### 2.3 키 저장 옵션

- **기본(권장):** 메모리 보관. 탭 닫으면 사라짐.
- **`이 브라우저에 키 저장` 체크 시:** localStorage 미러링. 다음 방문 시 자동 복구.
- **`지우기` 버튼:** 즉시 메모리 + localStorage 에서 제거.

> 공용 PC에서는 절대 `브라우저에 저장` 을 체크하지 마세요.

---

## 3. 보안 모델

### 3.1 키는 어디로 가나?

```
┌────────┐   1. X-OpenRouter-Key 헤더    ┌────────────┐
│ 브라우저 │ ─────────────────────────────▶ │  Go터뷰 서버  │
└────────┘                                │  (FastAPI)  │
                                          └──────┬─────┘
                                                 │ 2. Authorization: Bearer
                                                 ▼
                                          ┌────────────┐
                                          │ OpenRouter │
                                          └────────────┘
```

- 키는 **HTTPS 요청 헤더**로 우리 서버에 도착
- 우리 서버는 키를 **OpenRouter 호출에만 사용**하고 **즉시 폐기** (요청 수명 한정)
- DB·로그·디스크에 **저장하지 않음**
- 로깅이 필요한 경우 `mask_key()` 거쳐 `sk-or-v1-...ab12` 형태로만 기록

### 3.2 키 노출 방지 장치

| 위협 | 대응 |
|---|---|
| 응답 본문에 키 누출 | API 응답은 `key_preview` (마스킹) 만 포함 |
| 에러 메시지에 키 누출 | OpenRouter SDK 예외를 잡아 타입명만 반환 (`backend/routers/interview.py`) |
| 로그에 키 누출 | `mask_key()` 헬퍼 강제 (`backend/services/key_validator.py`) |
| 브라우저 저장 노출 | 기본 비활성, 명시적 체크박스 동의 시에만 |
| 다른 사용자 키 사용 | 키는 매 요청 헤더로 수신 → 세션·DB 공유 없음 |
| 클라이언트→서버 평문 전송 | 운영 시 HTTPS 필수 (CORS 설정 참고) |

### 3.3 사용자 안내 문구 (UI 노출용)

> "키는 우리 서버를 거치지만 어디에도 저장되지 않으며, OpenRouter 호출에만 사용됩니다. 브라우저 저장은 사용자가 명시적으로 체크할 때만 활성화됩니다."

---

## 4. 개발자 가이드

### 4.1 헤더 프로토콜

모든 면접 관련 엔드포인트에서 다음 두 헤더를 **선택적으로** 받습니다.

| 헤더 | 예시 | 미제공 시 동작 |
|---|---|---|
| `X-OpenRouter-Key` | `sk-or-v1-...` | Bedrock 자동 사용 |
| `X-LLM-Model` | `anthropic/claude-sonnet-4.6` | OpenRouter 기본 모델 |

응답에는 **항상** `X-Backend-Used` 헤더가 포함되어 실제 사용된 백엔드(`bedrock` 또는 `openrouter`)를 알려줍니다.

### 4.2 엔드포인트

#### `POST /api/byok/validate`

요청 (헤더 우선, 바디 폴백):

```http
POST /api/byok/validate
X-OpenRouter-Key: sk-or-v1-abc123...
Content-Type: application/json

{}
```

응답 (성공):

```json
{
  "valid": true,
  "label": "gofactory",
  "credit_left": 9.87,
  "models_count": 312,
  "error": null,
  "key_preview": "sk-or-v1-...c123"
}
```

응답 (실패):

```json
{
  "valid": false,
  "label": null,
  "credit_left": null,
  "models_count": null,
  "error": "키 형식이 올바르지 않습니다. 'sk-or-v1-'로 시작하는 키를 입력하세요.",
  "key_preview": "sk-or-v1-...xxxx"
}
```

#### `GET /api/byok/models`

응답:

```json
{
  "default": "anthropic/claude-sonnet-4.6",
  "models": {
    "anthropic/claude-sonnet-4.6": "Claude Sonnet 4.6 (균형, 추천)",
    "openai/gpt-4o": "GPT-4o (OpenAI 최신)",
    "google/gemini-2.5-pro": "Gemini 2.5 Pro (Google)"
  }
}
```

#### `POST /api/question`, `POST /api/evaluate`

기존 엔드포인트를 그대로 사용하되, 위의 BYOK 헤더가 있으면 자동으로 OpenRouter 경로로 라우팅됩니다.

### 4.3 아키텍처

```
┌─────────────────────────────────────────────────┐
│  FastAPI Router (interview.py)                  │
│  ├ Depends(_build_router) — 헤더 → LLMRouter     │
│  └ response.headers["X-Backend-Used"] = ...      │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│  LLMRouter (services/llm_router.py)             │
│  ├ user_key 있음? ─Yes─▶ OpenRouterClient        │
│  └          없음/형식오류 ─▶ BedrockClient        │
│  ├ validate_user_key() — runtime 검증            │
│  └ key_preview() — 마스킹된 안전 식별자          │
└─────────────────────────────────────────────────┘
                       ▲
                       │
┌─────────────────────────────────────────────────┐
│  key_validator (services/key_validator.py)      │
│  ├ is_well_formed() — sk-or-v1- prefix + length │
│  ├ mask_key() — 로깅 안전 마스킹                 │
│  └ validate_openrouter_key() — /auth/key 호출   │
└─────────────────────────────────────────────────┘
```

### 4.4 신규/변경 파일 목록

**신규:**

- `backend/routers/byok.py` — `/api/byok/validate`, `/api/byok/models`
- `backend/services/key_validator.py` — 형식 + 실제 검증 + 마스킹
- `docs/BYOK_GUIDE.md` — 본 문서

**수정:**

- `backend/services/llm_router.py` — `validate_user_key`, `is_well_formed_key`, `key_preview` 추가
- `backend/routers/interview.py` — `AIService` → `LLMRouter` (헤더 의존성 주입 + `X-Backend-Used` 응답 헤더)
- `backend/main.py` — `byok` 라우터 등록, CORS `expose_headers` 추가
- `frontend/index.html` — BYOK 패널 + 백엔드 배지 추가
- `frontend/js/app.js` — `apiCall` 에 헤더 주입, 모델 카탈로그 로드, 검증 버튼, localStorage 옵션
- `frontend/css/style.css` — BYOK 섹션·배지 스타일 + 다크모드
- `app.py` (Streamlit) — 사이드바 BYOK 입력, `_ByokAwareClient` 어댑터, `get_ai_client` 교체

---

## 5. 테스트 시나리오

### 5.1 키 없이 호출 (기본 흐름)

1. 브라우저 시크릿 모드로 접속
2. BYOK 패널은 펼치지 않음
3. 직무 선택 → 면접 시작
4. **기대:** 질문 생성됨 + 상단 배지 `📡 Bedrock` 유지
5. **확인:** DevTools Network 탭에서 `/api/question` 응답 헤더 `X-Backend-Used: bedrock`

### 5.2 잘못된 키 입력

1. BYOK 패널 펼치기
2. 키 입력란에 `sk-invalid-12345` 입력
3. `키 검증` 클릭
4. **기대:** ❌ "키 형식이 올바르지 않습니다..." 표시
5. **추가:** `sk-or-v1-` 시작하지만 가짜 키 입력 → ❌ "키가 유효하지 않습니다 (401 Unauthorized)"

### 5.3 올바른 키 입력

1. 실제 OpenRouter 키 입력 → `키 검증`
2. **기대:** ✅ "키 유효 · 라벨: ... · 잔액: $X.XX · 모델: NNN개 · (sk-or-v1-...abcd)"
3. 면접 시작 → 질문 생성
4. **확인:** 응답 헤더 `X-Backend-Used: openrouter`, 상단 배지 `🔑 OpenRouter`

### 5.4 키 입력 후 모델 변경

1. 키 검증 완료 상태에서 모델 드롭다운 → `openai/gpt-4o-mini` 선택
2. 다음 면접 질문 요청
3. **기대:** 같은 키로 GPT-4o-mini 응답 (응답 스타일이 다를 수 있음)

### 5.5 키 검증 시 잔액·라벨 표시

- OpenRouter 콘솔에서 key label 을 "gofactory-test", limit $10, usage $1.23 으로 발급
- 검증 결과: `라벨: gofactory-test · 잔액: $8.77`

### 5.6 localStorage 동작

1. `이 브라우저에 키 저장` 체크 → 키 입력 → 검증
2. 페이지 새로고침 → 키 입력란이 자동 복원
3. `지우기` 클릭 → 입력란 + localStorage 모두 비워짐

### 5.7 Streamlit 흐름

1. `streamlit run app.py` 실행
2. 사이드바 `🔑 OpenRouter API 키 (선택)` 펼침
3. 키 입력 → 모델 선택 → `키 검증`
4. 면접 시작 → 사이드바 `📍 현재 백엔드: 🔑 OpenRouter` 확인
5. 키를 빈 문자열로 변경 → 다음 호출은 다시 Gemini/Bedrock 흐름

---

## 6. 운영 시 알려진 가정·제약

| 항목 | 가정 | 영향 |
|---|---|---|
| OpenRouter `/auth/key` 응답 스키마 | `{"data": {"label", "usage", "limit", "is_free_tier"}}` | 스키마 변경 시 `label`/`credit_left` 가 null로 표시 (검증 자체는 동작) |
| OpenRouter 모델 카탈로그 | `SUPPORTED_MODELS` 하드코딩 | 최신 모델 추가 필요 시 `openrouter_client.py` 직접 수정 |
| `/auth/key` 의 401 정확도 | OpenRouter 가 만료/오타 키에 일관되게 401 반환 | 다른 4xx 도 "검증 실패" 로 묶어 표시 |
| 음성 전사 (transcribe_audio) | LLMRouter 미지원 (NotImplementedError) | Streamlit 측 어댑터가 AIClient 의 Gemini 전사로 자동 폴백 |
| Streamlit `get_ai_client()` 호환 | `generate_question`, `evaluate_answer` 시그니처 일치 | 그 외 메서드(`generate_targeted_question` 등)는 AIClient 로 위임 |
| 다중 사용자 동시 검증 | OpenRouter rate limit 도달 가능 | 검증 타임아웃 8초로 제한 + retry 미포함 |

---

## 7. 자주 묻는 질문 (FAQ)

**Q. 키 입력 안 하면 진짜 무료인가요?**
A. 네. AWS 학생 크레딧으로 Bedrock 비용을 운영자가 부담합니다. 다만 크레딧 소진 시 서비스가 일시 중단될 수 있어요.

**Q. 키를 입력하면 OpenRouter 에 직접 청구되나요?**
A. 네. OpenRouter 측 잔액에서 차감됩니다. 우리 서버는 단순 패스스루입니다.

**Q. 키가 노출될 위험은요?**
A. 운영 환경에서 HTTPS 사용 시, 키는 (a) 브라우저 ↔ 우리 서버, (b) 우리 서버 ↔ OpenRouter 두 구간에서만 평문이 됩니다. 둘 다 TLS 로 보호됩니다. 우리 서버는 키를 저장하지 않습니다.

**Q. 어느 모델이 좋아요?**
A. 균형: Claude Sonnet 4.6 · 저렴: Claude Haiku 4.5 또는 GPT-4o-mini · 최고품질: Claude Opus 4.7.
