# Go터뷰 MCP 사용 가이드

> Claude Pro / Max 구독자는 **추가 결제 없이** 본인의 Claude 정액으로 Go터뷰 면접 연습을 사용할 수 있습니다.

---

## 한 줄 요약

Claude Desktop 설정에 우리 MCP 서버 URL 한 줄만 추가하면, **Claude 채팅창 안에서** 회사·직무 선택 → 질문 → 답변 → 평가 → 기록까지 한 흐름으로 진행됩니다. LLM 호출은 **사용자의 Claude 구독에서 발생**하므로 우리 인프라 비용 0, 사용자 추가 비용 0.

---

## 1. 사전 준비

| 항목 | 요건 |
|---|---|
| 구독 | Claude Pro ($20/월) 이상 |
| 앱 | Claude Desktop (macOS / Windows) 최신 버전 |
| OS | 무관 (URL 기반이라 모든 OS 가능) |

---

## 2. 설정 (1분)

### 2-1. 설정 파일 위치

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

파일이 없으면 새로 만드세요.

### 2-2. 다음 내용 입력

```json
{
  "mcpServers": {
    "goterview": {
      "url": "http://54.226.87.66:8000/mcp/",
      "transport": "streamable-http"
    }
  }
}
```

> URL 끝의 `/` 빠뜨리지 마세요. EC2 IP가 바뀌면 같은 자리만 교체.

### 2-3. Claude Desktop 재시작

설정창에서 MCP 서버 목록에 `goterview` ⚪️ 가 보이면 성공.

---

## 3. 사용법

Claude에게 자연어로 말하면 됩니다. 예시:

```
"고터뷰로 삼성전자 회로설계 면접 연습하고 싶어"
```

Claude는 자동으로:
1. `list_companies` 호출 → 캐시 회사 확인
2. `get_company_context("삼성전자")` 호출 → 인재상·주력사업·트렌드 수집
3. `get_evaluation_rubric("회로설계")` 호출 → 평가 루브릭 수집
4. 회사·직무 컨텍스트 반영한 면접 질문 생성
5. 사용자 답변 받기
6. 루브릭 따라 5축 평가 + 점수 산출
7. `save_interview_record(...)` 호출 → DB 저장
8. 다음 질문 또는 약점 분석 제안

복기 예시:

```
"내가 지금까지 본 면접 중 약점이 뭐였어?"
→ Claude가 get_weakness_analysis() 호출 → 약점 축 응답
```

---

## 4. 노출 도구 6종

| 도구 | 설명 |
|---|---|
| `list_companies()` | 캐시된 회사 목록 (현재 5개사) |
| `get_company_context(company_name)` | 인재상·주력사업·최신 트렌드 |
| `get_evaluation_rubric(job_field, interview_type)` | 5축 평가 루브릭 + 회피성 답변 패턴 |
| `save_interview_record(...)` | 면접 결과 DB 저장 |
| `get_recent_history(limit)` | 최근 면접 기록 N건 |
| `get_weakness_analysis()` | 5축 평균 비교로 약점 식별 |

---

## 5. 왜 MCP인가?

| 비교 항목 | 기존 BYOK (OpenRouter 키) | **MCP (이 가이드)** |
|---|---|---|
| 사용자 진입 | OpenRouter 가입 → 결제 카드 → 키 발급 | Claude Desktop 설정 1줄 |
| 추가 결제 | 사용량별 종량제 | **0** (정액 구독 활용) |
| 우리 인프라 비용 | LLM 호출 대행으로 발생 | **0** (LLM은 사용자 측에서) |
| UI | Go터뷰 자체 웹 | Claude Desktop 채팅창 |
| 모바일 | ✅ | Claude 모바일 앱 MCP 지원 시점 후 |

---

## 6. 트러블슈팅

| 증상 | 원인·해결 |
|---|---|
| 설정창에 `goterview` 안 보임 | JSON 문법 오류. 콤마·따옴표 확인 후 Claude 재시작 |
| ⚪️ 가 ❌로 표시 | 서버가 꺼져있거나 URL 오타. 브라우저로 `http://54.226.87.66:8000/api/health` 접속해 200 확인 |
| 도구 호출 시 "permission denied" | Claude Desktop 설정 → MCP → goterview의 도구 허용 토글 |
| 응답 한국어 깨짐 | macOS/Linux는 정상. Windows에서 Claude 버전 < 0.7이면 업데이트 |

---

## 7. 현재 한계 (다음 작업으로 해결 예정)

- 캐시 회사 5개사만 풍부한 컨텍스트 (확장 예정: 20개사 → AWS Batch 주1회 자동 갱신)
- 평가 루브릭이 직무별로 동일 (Phase 2: 직무 12종 각각의 키워드·가중치 차별화)
- 사용자별 기록 분리 없음 (Phase 3: 인증 추가 후 분리)

---

## 부록: 로컬 개발자용 stdio 연결

서버를 로컬에서 직접 실행하고 싶다면:

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. stdio transport로 실행
python -c "from backend.mcp_server import mcp; mcp.run(transport='stdio')"
```

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "goterview-local": {
      "command": "python",
      "args": ["-c", "from backend.mcp_server import mcp; mcp.run(transport='stdio')"],
      "cwd": "/path/to/gofactory-v3"
    }
  }
}
```
