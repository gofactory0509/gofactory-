"""Pydantic 요청/응답 모델 정의.

FastAPI 엔드포인트에서 사용하는 모든 요청/응답 스키마를 정의한다.
"""

from pydantic import BaseModel, Field


# --- Request Models ---


class QuestionRequest(BaseModel):
    """면접 질문 생성 요청 모델."""

    job_field: str = Field(..., min_length=1, description="직무 분야")


class EvaluationRequest(BaseModel):
    """답변 평가 요청 모델."""

    job_field: str = Field(..., min_length=1, description="직무 분야")
    question: str = Field(..., min_length=1, description="면접 질문")
    answer: str = Field(..., min_length=1, description="지원자 답변")


# --- Response Models ---


class QuestionResponse(BaseModel):
    """면접 질문 생성 응답 모델."""

    question: str


class FeedbackResponse(BaseModel):
    """답변 평가 피드백 응답 모델."""

    feedback: str
    score: int | None = None
    logic_score: str
    keywords: str
    improvements: str
    summary: str


class InterviewRecord(BaseModel):
    """면접 기록 단일 레코드 모델."""

    id: int
    date: str
    job_field: str
    question: str
    answer: str
    feedback: str
    score: int | None


class RecordsResponse(BaseModel):
    """면접 기록 목록 응답 모델."""

    records: list[InterviewRecord]


class StatsResponse(BaseModel):
    """통계 응답 모델."""

    total_interviews: int
    avg_score: float | None
    most_practiced_field: str | None
    job_distribution: dict[str, int]
    question_bank_size: int


class QuoteResponse(BaseModel):
    """오늘의 명언 응답 모델."""

    quote: str


class HealthResponse(BaseModel):
    """헬스체크 응답 모델."""

    status: str
    timestamp: str


class ErrorResponse(BaseModel):
    """에러 응답 모델."""

    detail: str
