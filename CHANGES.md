# Go터뷰 V3 변경 사항

V3의 핵심은 **반도체 산업 특화 + 사업부 단위 면접 맥락 강화**입니다.
삼성전자 DS부문 '26상 공채 직무기술서(PDF 62p)를 기준으로 직무 카탈로그를 전면 재구성했습니다.

---

## 한눈에 보기

| 영역 | V2 (이전) | V3 (현재) |
|---|---|---|
| 직무 카탈로그 | 반도체 / 백엔드 / 데이터 / 마케팅 (4개) | 반도체 산업 10개 직무 (삼성 직무기술서 기준) |
| 사업부 구분 | 없음 | 직무별 모집 사업부 선택 가능 (메모리/Foundry/S.LSI/AI센터 등) |
| 시드 질문 수 | 4직무 × 7 = 28개 | 10직무 × 7 = 70개 |
| AI 프롬프트 | 직무명만 전달 | 직무 + **사업부 컨텍스트** (주력 제품·핵심 기술·최근 동향) |
| "기타 (직접 입력)" 옵션 | 있음 | 제거 — 반도체 산업 한정 |
| 기존 면접 기록 | — | **8건 보존** (마이그레이션) |

---

## 1. database.py

### 변경 요약
- **추가** `JOB_DESCRIPTIONS` — 10개 직무 1줄 설명
- **추가** `JOB_BUSINESS_UNITS` — 직무 → 모집 사업부 매핑
- **교체** `SEED_QUESTIONS` — 옛 4직무 → 신규 10직무 (PDF Role/Requirements 기반)
- **스키마** `interviews.business_unit TEXT` 컬럼 ALTER 마이그레이션
- **재시드** 옛 시드 데이터 자동 삭제 + 신규 70개 삽입 로직
- **시그니처** `save_interview()` 에 `business_unit` 파라미터 추가

### 핵심 데이터 구조

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

### 재시드 로직 (핵심)
```python
# 새 직무 시드가 없으면(=옛 카탈로그면) 전체 삭제 후 신규 삽입
cursor = self.conn.execute(
    f'SELECT COUNT(*) FROM common_questions WHERE job_field IN ({placeholders})',
    list(SEED_QUESTIONS.keys()),
)
if cursor.fetchone()[0] > 0:
    return
self.conn.execute('DELETE FROM common_questions')
# ... 새 시드 삽입
```

### 스키마 마이그레이션
```python
for ddl in (
    'ALTER TABLE interviews ADD COLUMN interview_type TEXT DEFAULT "직무면접"',
    'ALTER TABLE interviews ADD COLUMN business_unit TEXT',
):
    try:
        self.conn.execute(ddl)
    except Exception:
        pass  # 컬럼 이미 있으면 무시
```

---

## 2. app.py

### 변경 요약
- **import** `JOB_BUSINESS_UNITS, JOB_DESCRIPTIONS` 추가
- **상수** `JOB_FIELDS = list(JOB_BUSINESS_UNITS.keys())` — DB와 단일 출처
- **제거** "기타 (직접 입력)" 옵션 (반도체 산업 한정)
- **session** `business_unit: None` 추가
- **UI** 사이드바에 사업부 선택 라디오 + 직무 설명 캡션 추가
- **면접** 헤더에 사업부 표시, AI 호출·DB 저장 시 `business_unit` 전달
- **기록** 면접 기록 expander에 사업부 함께 표시

### 핵심 UI 로직

```python
# 직무 선택 + 직무 설명 캡션
selected_job = st.selectbox("면접 직무를 선택하세요", JOB_FIELDS, ...)
if selected_job and JOB_DESCRIPTIONS.get(selected_job):
    st.caption(JOB_DESCRIPTIONS[selected_job])

# 사업부 선택 (해당 직무가 모집되는 곳만)
available_units = JOB_BUSINESS_UNITS.get(selected_job, [])
if len(available_units) == 1:
    selected_business_unit = available_units[0]
    st.caption(f"이 직무는 **{selected_business_unit}** 에서 모집됩니다")
else:
    selected_business_unit = st.radio("면접 대상 사업부", available_units, ...)
```

### 면접 헤더 표시
```python
job_label = f"{job_field}" + (f" ({business_unit})" if business_unit else "")
header_text = f"{emoji} {job_label} - {interview_type}"
if company:
    header_text += f" / {company}"
```

---

## 3. ai_client.py

### 변경 요약
- **시그니처** `generate_question(..., business_unit: str = "")` 추가
- **시그니처** `evaluate_answer(..., business_unit: str = "")` 추가
- **프롬프트** 사업부 컨텍스트 주입 — 주력 제품·핵심 기술·최근 동향 반영 지시

### 질문 생성 프롬프트
```python
job_context = f"'{job_field}'"
if business_unit:
    job_context += f" 직무 (사업부: {business_unit})"
    company_context += f"사업부 '{business_unit}'의 특성(주력 제품, 핵심 기술, 최근 동향)을 반영한 질문을 만들어줘. "
```

### 답변 평가 프롬프트
```python
bu_context = ""
if business_unit:
    bu_context = f"사업부: {business_unit}\n해당 사업부의 주력 제품·핵심 기술과 답변의 적합성을 함께 평가해줘.\n"
```

---

## 데이터 마이그레이션 동작

기존 `interviews.db` 가 있을 때:

| 테이블 | 변경 |
|---|---|
| `interviews` | 기존 8건 기록 **그대로 보존** + `business_unit` 컬럼 추가 (옛 기록은 NULL) |
| `common_questions` | 옛 4직무 28개 시드 **자동 삭제** + 신규 10직무 70개 시드 삽입 |
| `question_bank` | 변경 없음 |
| `resumes` | 변경 없음 |
| `user_feedback` | 변경 없음 |

### 검증 출력
```
직무 수: 10
SEED_QUESTIONS 총 질문 수: 70
common_questions:
  SW개발: 7개
  반도체공정기술: 7개
  반도체공정설계: 7개
  생산관리: 7개
  설비기술: 7개
  신호및시스템설계: 7개
  인프라기술: 7개
  평가및분석: 7개
  환경: 7개
  회로설계: 7개
interviews 컬럼: id, date, job_field, interview_type, business_unit, question, answer, feedback, score, ...
기존 interviews 기록: 8건 보존
```

---

## 실행 방법

V3의 3개 파일을 원본 위치([../Go면접_앱파일](../Go면접_앱파일))에 덮어쓰거나, V3 폴더 자체를 앱 디렉토리로 사용.

```powershell
cd "Go터뷰_V3"
streamlit run app.py
```

> 의존성 동일: streamlit, google-generativeai, openai, python-dotenv

---

## 출처

- 삼성전자 DS부문 2026년 상반기 3급 신입사원 채용 직무기술서 (PDF, 62쪽)
- 채용 페이지: https://www.samsung-dsrecruit.com/
- 직무 분류: 메모리 / S.LSI / Foundry / CTO_반도체연구소 / 글로벌 제조&인프라 / TSP총괄 / AI센터 / 부문공통(경영지원 — 제외)
