# Go터뷰 V3 → V4 아키텍처 설계
## 회사 정보 시스템 (Hybrid Cache) + AWS Batch 파이프라인

---

## 핵심 문제

면접 시 회사명 입력 → AI가 그 회사의 **인재상·최신 트렌드·주력 사업** 반영한 질문/평가 필요.
현재는 회사명만 프롬프트에 들어가고, 회사 정보는 LLM의 학습 데이터에 의존 → 정확도·최신성 한계.
(특히 HBM·AI 반도체처럼 최근 트렌드는 LLM이 모르거나 부정확)

---

## 해결: 하이브리드 캐시 시스템

```
┌─────────────────────────────────────────────────────────────┐
│                        실시간 트랙                            │
├─────────────────────────────────────────────────────────────┤
│  [사용자] 회사명: "삼성전자"                                  │
│        ↓                                                     │
│  [FastAPI] GET /api/companies/{name}                         │
│        ↓                                                     │
│  ┌──[캐시 DB 조회]──┐                                        │
│  │                  │                                        │
│  HIT              MISS                                       │
│  │                  │                                        │
│  ↓                  ↓                                        │
│  즉시 반환     실시간 검색 (네이버 API + DART)               │
│  (12개 주력)        ↓                                        │
│                  결과 캐시 저장                              │
│  │                  │                                        │
│  └──────┬───────────┘                                        │
│         ↓                                                    │
│  [AI 클라이언트] 회사 컨텍스트 주입 → Gemini 호출            │
│         ↓                                                    │
│  [사용자에게] 회사 맞춤 면접 질문/평가                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   AWS Batch 정기 갱신 트랙                   │
├─────────────────────────────────────────────────────────────┤
│  [EventBridge] cron(0 17 ? * SUN *)                         │
│  (매주 일요일 02:00 KST = UTC 17:00 SAT)                    │
│        ↓                                                     │
│  [AWS Batch Job Queue]                                       │
│  Job Def: ECR 이미지 (Python + BeautifulSoup + boto3)        │
│  Fargate Spot (~$0.05/실행)                                  │
│        ↓                                                     │
│  각 주력 회사별 (12개 × ~30초 = 약 5분):                     │
│  • 채용 페이지 인재상 스크래핑                               │
│  • 네이버 뉴스 API (최근 7일)                                │
│  • DART OpenAPI (공시)                                       │
│        ↓                                                     │
│  [S3] s3://gofactory-data/companies/raw/{name}_{date}.json   │
│        ↓                                                     │
│  [Lambda] LLM으로 요약 → RDS UPSERT                          │
│        ↓                                                     │
│  [RDS PostgreSQL] companies 테이블 갱신                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 캐시 대상 회사 (추천 12개)

한국 주요 반도체 기업 — 매출·채용 규모·뉴스 노출도 기준:

| 분류 | 회사 | 비고 |
|---|---|---|
| IDM (메모리·시스템) | **삼성전자** (DS부문) | 직무기술서 기준 회사 |
| | **SK하이닉스** | HBM 글로벌 1위 |
| Foundry | **DB하이텍** | 국내 8인치 파운드리 |
| 팹리스 | **매그나칩반도체** | DDI 강자 |
| 장비 | **한미반도체** | HBM TC Bonder 독점 |
| | **원익IPS** | 식각·증착 장비 |
| | **파크시스템스** | 측정 장비 (글로벌) |
| 소재 | **솔브레인** | HBM용 화학소재 |
| | **동진쎄미켐** | 포토레지스트 |
| | **SK실트론** | 웨이퍼 |
| 외국계 한국법인 | **ASML 코리아** | EUV 노광 |
| | **어플라이드머티어리얼즈(AMAT) 코리아** | 종합 장비 |

---

## 데이터 소스 옵션

| 데이터 종류 | 옵션 A | 옵션 B | 추천 |
|---|---|---|---|
| 인재상 | 회사 채용 페이지 크롤링 (BeautifulSoup) | LLM Web Search Tool | **A** (정확·무료) |
| 최근 트렌드 | 네이버 뉴스 검색 API (무료, 25,000회/일) | Google News RSS | **A** (한국 특화) |
| 공시·재무 | DART OpenAPI (무료, 한국 공시) | — | **A** |
| 채용 동향 | 회사 채용 페이지 + 잡코리아 | — | A (선택) |

---

## companies 테이블 스키마

```sql
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,              -- "삼성전자"
    aliases TEXT,                            -- "삼성, Samsung, SEC" (검색 보조)
    industry TEXT,                           -- "반도체-메모리"
    talent_profile TEXT,                     -- 인재상 요약 (~200자)
    recent_news_summary TEXT,                -- 최근 트렌드 요약 (~300자)
    business_focus TEXT,                     -- 주력 사업 (HBM, AI 반도체 등)
    recruiting_status TEXT,                  -- 채용 동향 (선택)
    source_urls JSON,                        -- 원본 URL 배열
    last_updated TIMESTAMP NOT NULL,
    is_cached BOOLEAN DEFAULT TRUE           -- false면 실시간 조회 결과
);

CREATE INDEX idx_companies_aliases ON companies(aliases);
```

---

## AWS Batch 파이프라인

### 컴포넌트
- **Trigger**: EventBridge (cron 스케줄)
- **Compute**: AWS Batch on Fargate Spot ($0.04/vCPU-hour)
- **Container**: ECR에 Python 이미지 (`crawler.py` + 의존성)
- **Storage**: S3 (raw JSON) + RDS PostgreSQL (정제 데이터)
- **Post-processing**: Lambda (S3 PUT 이벤트 → LLM 요약 → RDS UPSERT)

### Batch Job 코드 구조
```python
# crawler.py (Batch job 진입점)
import boto3, json
from datetime import datetime
from scrapers import scrape_recruit_page, fetch_naver_news, fetch_dart

COMPANIES = [...]  # 12개 목록

def main():
    s3 = boto3.client('s3')
    today = datetime.now().strftime('%Y-%m-%d')
    for company in COMPANIES:
        data = {
            'name': company['name'],
            'recruit_html': scrape_recruit_page(company['recruit_url']),
            'news': fetch_naver_news(company['name'], days=7),
            'dart': fetch_dart(company['corp_code']),
            'crawled_at': datetime.utcnow().isoformat(),
        }
        s3.put_object(
            Bucket='gofactory-data',
            Key=f"companies/raw/{company['name']}_{today}.json",
            Body=json.dumps(data, ensure_ascii=False).encode('utf-8'),
        )

if __name__ == '__main__':
    main()
```

### 비용 추정 (월 기준)
| 항목 | 비용 |
|---|---|
| Batch (Fargate Spot, 주 1회 × 5분) | ~$0.05/월 |
| Lambda (요약 처리, 12 invocations/주) | ~$0.01/월 |
| RDS db.t4g.micro | ~$15/월 (또는 free tier) |
| S3 (raw 데이터 100MB) | ~$0.003/월 |
| **합계** | **~$15/월** (RDS free tier 시 $0.10) |

---

## FastAPI 엔드포인트 (V4 베이스)

향후 React+FastAPI 변환 시 사용할 엔드포인트:

```python
# GET /api/companies/{name}
# 캐시 hit → 즉시 반환 / miss → 실시간 검색 후 캐시 저장 + 반환
# Response:
{
  "name": "삼성전자",
  "talent_profile": "도전·창의·실패를 두려워하지 않는 인재...",
  "recent_news_summary": "2026년 HBM4 양산 본격화, AI 반도체 마하-1 발표...",
  "business_focus": "DRAM, NAND, Foundry, AI Accelerator",
  "last_updated": "2026-05-25T02:00:00Z",
  "source": "cached"  # 또는 "live"
}

# GET /api/companies
# 캐시된 회사 목록 (자동완성용)

# POST /api/interview/start
# Body: { job_field, business_unit, interview_type, company }
# → 내부적으로 /companies/{company} 호출해서 AI 프롬프트 enrich
```

---

## V3 → V4 마이그레이션 단계

1. **로컬 SQLite로 PoC** — `companies` 테이블 추가, 5개 회사 수동 시드
2. **간단한 크롤러 1개 작성** — Python script로 삼성전자 데이터 가져오기
3. **AI 프롬프트에 회사 정보 주입** — `ai_client.evaluate_answer()`에 `talent_profile` 전달
4. **AWS 배포** — RDS PostgreSQL 마이그레이션, Batch + EventBridge 셋업
5. **FastAPI 분리** — Streamlit → React+FastAPI 전환 시 자연스럽게 통합

---

## 발표·평가 관점에서 어필 포인트

- **"비용 효율적인 하이브리드 캐시"** — 100% 실시간 호출 대비 99% 비용 절감
- **"AWS Batch + EventBridge + RDS + S3 통합"** — AWS 강의 점수
- **"BYOK + AWS 인프라 분리"** — LLM 비용 사용자 부담, AWS 비용만 자체 부담 (월 $0.10~$15)
- **"한국 반도체 산업 특화"** — 삼성 직무기술서 기반, DART·네이버 API 활용

---

## 다음 의사결정 (승혁님)

### ① 캐시 회사 목록
A) 위 추천 12개 그대로  
B) 일부 제외 / 추가  
C) 다른 셋  

### ② 데이터 소스 우선순위
A) 네이버 뉴스 + DART + 채용 페이지 크롤링 (한국 특화, 무료, 추천)  
B) Google Search API + Wikipedia (국제 표준)  
C) LLM Web Search Tool (가장 간단하지만 비용↑)  

### ③ AWS Batch 갱신 주기
A) 매주 1회 (일요일 새벽) — 비용 최소, 트렌드는 1주 단위로 변함  
B) 매일 1회 — 트렌드 빠른 반영, 비용 7배  
C) 트리거 기반 (수동/이벤트)  

### ④ MVP 범위 (이번 학기 발표 기준)
A) 로컬 SQLite + 5개 회사 수동 시드 (1주, 가장 빠름)  
B) 로컬 SQLite + 크롤러 1개 PoC (2주)  
C) AWS Batch + RDS 풀스택 (3주, AWS 점수↑)  

---

## 추천 진행 경로

발표 일정 + AWS 강의 점수 고려:

| 시기 | 작업 |
|---|---|
| **1주차** (이번 주) | A-A-A-A 조합 → 로컬 SQLite에 5개 회사 수동 시드 + AI 프롬프트 통합 |
| **2주차** | 크롤러 1개 작성 (삼성전자 PoC) |
| **3주차** | AWS Batch + RDS 배포, EventBridge 연동 |
| **발표 직전** | 통합 테스트, 시연 시나리오 준비 |

매주 demo 가능한 상태 유지하면서 점진적으로 AWS 색채 강화.
