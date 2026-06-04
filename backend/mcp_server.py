# -*- coding: utf-8 -*-
"""Go터뷰 MCP(Model Context Protocol) 서버.

Claude Desktop 등 MCP 호환 클라이언트에서 사용자의 구독 LLM
(예: Claude Pro/Max 정액)으로 면접 연습을 진행할 수 있게 한다.

설계 원칙
---------
- 이 서버는 **LLM 호출을 하지 않는다**. 회사 컨텍스트·평가 루브릭·기록
  저장 도구만 노출한다. LLM 호출은 사용자 측 Claude가 수행 →
  사용자 구독 토큰에서 차감 → 우리 인프라 비용 0.
- 우리 캐시 자산(인재상·주력사업·최신트렌드)과 도메인 지식
  (5축 평가 루브릭)이 사용자의 Claude 채팅 흐름에 자연스럽게 주입되도록 한다.

마운트
------
``backend/main.py`` 의 FastAPI 인스턴스에 ``/mcp`` 경로로 mount.
사용자는 Claude Desktop 설정에 ``http://<host>:8000/mcp`` 를 등록.
"""
from __future__ import annotations

from fastmcp import FastMCP

from backend.config import settings
from backend.services.evaluation import build_rubric
from database import InterviewDB  # 루트 모듈 — 회사 정보 캐시 보유


mcp = FastMCP("goterview")

_db: InterviewDB | None = None


def _get_db() -> InterviewDB:
    """프로세스 단위로 단일 InterviewDB 인스턴스 lazily 생성."""
    global _db
    if _db is None:
        _db = InterviewDB(settings.database_path)
    return _db


# ─────────────────────────────────────────────────────────────
# 도구 1: 회사 목록
# ─────────────────────────────────────────────────────────────
@mcp.tool()
def list_companies() -> list[dict]:
    """Go터뷰가 캐시 중인 회사 목록을 반환한다.

    사용 시점: 사용자가 어떤 회사 면접을 원할지 묻기 전에 옵션을 보여줄 때.

    Returns:
        각 항목 ``{"name": str, "industry": str, "updated_at": str}`` 의 리스트.
    """
    return _get_db().list_cached_companies()


# ─────────────────────────────────────────────────────────────
# 도구 2: 회사 컨텍스트
# ─────────────────────────────────────────────────────────────
@mcp.tool()
def get_company_context(company_name: str) -> dict:
    """특정 회사의 인재상·주력 사업·최신 트렌드 컨텍스트를 반환한다.

    이 컨텍스트는 면접 질문 생성과 답변 평가 모두에 반영되어야 한다.
    Claude는 응답할 때 이 회사의 talent_profile 키워드를 평가에 가중치로 사용한다.

    Args:
        company_name: 회사 한글명 (예: "삼성전자", "SK하이닉스").

    Returns:
        캐시에 있으면 ``{"name", "industry", "talent_profile", "business_focus",
        "recent_news_summary", "updated_at"}`` dict.
        없으면 ``{"error": ..., "available": [...]}`` 로 사용 가능 회사 안내.
    """
    info = _get_db().get_company_info(company_name)
    if info is None:
        return {
            "error": f"'{company_name}' 회사 정보가 캐시에 없습니다.",
            "available": [c["name"] for c in _get_db().list_cached_companies()],
            "hint": "캐시 없는 회사라도 Claude는 본인의 일반 지식으로 면접 진행 가능합니다.",
        }
    return info


# ─────────────────────────────────────────────────────────────
# 도구 3: 평가 루브릭
# ─────────────────────────────────────────────────────────────
@mcp.tool()
def get_evaluation_rubric(
    job_field: str,
    interview_type: str = "직무면접",
) -> dict:
    """직무·면접유형별 평가 루브릭(5축 채점 가이드)을 반환한다.

    Claude는 답변을 평가할 때 반드시 이 루브릭의 ``output_format`` 을 따르고,
    ``auto_low_score_patterns`` 에 해당하는 회피성 답변은 30점 이하를 강제한다.
    ``minimum_answer_length`` 미만은 결정론적으로 감점한다.

    Args:
        job_field: 직무 이름 (예: "회로설계", "메모리설계").
        interview_type: "직무면접" | "인성면접" | "자소서기반면접".

    Returns:
        ``{"axes", "scoring_scale", "type_focus", "minimum_answer_length",
        "auto_low_score_patterns", "output_format"}`` 의 dict.
    """
    return build_rubric(job_field, interview_type)


# ─────────────────────────────────────────────────────────────
# 도구 4: 면접 결과 저장
# ─────────────────────────────────────────────────────────────
@mcp.tool()
def save_interview_record(
    job_field: str,
    question: str,
    answer: str,
    feedback: str,
    score: int,
) -> dict:
    """완료한 면접 한 라운드를 기록 DB에 저장한다.

    Claude는 평가를 마친 직후 이 도구를 호출해야 사용자가 나중에
    ``get_recent_history`` 또는 ``get_weakness_analysis`` 로 복기할 수 있다.

    Args:
        job_field: 직무.
        question: 면접 질문 원문.
        answer: 사용자 답변 원문.
        feedback: Claude가 생성한 전체 피드백 텍스트.
        score: 총점 (0~100).

    Returns:
        ``{"saved": True, "score": int}`` — 저장 성공 여부.
    """
    db = _get_db()
    db.save_interview(
        job_field=job_field,
        question=question,
        answer=answer,
        feedback=feedback,
        score=score,
    )
    return {"saved": True, "score": score}


# ─────────────────────────────────────────────────────────────
# 도구 5: 최근 기록
# ─────────────────────────────────────────────────────────────
@mcp.tool()
def get_recent_history(limit: int = 10) -> list[dict]:
    """가장 최근에 저장된 면접 기록을 반환한다.

    사용 시점: 사용자가 "최근 면접 어땠어?" "지난번 답변 보여줘" 등을 물을 때.

    Args:
        limit: 반환할 기록 수 (기본 10, 최대 100).

    Returns:
        각 기록: ``{"timestamp", "job_field", "question", "answer", "feedback", "score"}``.
    """
    limit = max(1, min(limit, 100))
    records = _get_db().get_all_records()
    return records[:limit]


# ─────────────────────────────────────────────────────────────
# 도구 6: 약점 분석
# ─────────────────────────────────────────────────────────────
@mcp.tool()
def get_weakness_analysis() -> dict:
    """축적된 면접 기록으로부터 약점 영역을 분석한다.

    5축(논리성/직무적합성/구체성/표현력/차별성) 별 평균 점수를 비교해
    가장 낮은 축을 ``weakest_axis`` 로 보고하고, Claude가 그 축을
    파고드는 후속 질문을 직접 생성할 수 있게 한다.

    Returns:
        ``get_stats()`` 의 결과 dict (총 면접 수, 직무별 점수, 5축 평균 등).
    """
    return _get_db().get_stats()


__all__ = ["mcp"]
