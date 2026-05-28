# -*- coding: utf-8 -*-
"""Interview 라우터 모듈.

면접 질문 생성, 답변 평가, 오늘의 명언 엔드포인트를 제공한다.
"""

import random
from datetime import date

from fastapi import APIRouter, HTTPException, Request

from backend.models import (
    EvaluationRequest,
    FeedbackResponse,
    QuestionRequest,
    QuestionResponse,
    QuoteResponse,
)
from backend.services.ai_client import AIService

router = APIRouter()

# 오늘의 명언 (취업 준비생을 위한 동기부여 명언 30+)
DAILY_QUOTES = [
    "준비된 자에게 기회는 찾아온다.",
    "면접은 나를 보여주는 무대다.",
    "실패는 성공의 연습이다.",
    "꾸준함이 재능을 이긴다.",
    "오늘의 연습이 내일의 자신감이 된다.",
    "완벽한 답변보다 진솔한 답변이 낫다.",
    "긴장은 준비가 부족할 때 찾아온다.",
    "작은 성장도 성장이다.",
    "포기하지 않는 한 실패는 없다.",
    "나를 가장 잘 아는 사람은 나 자신이다.",
    "매일 1%씩 성장하면 1년 후 37배가 된다.",
    "면접관도 사람이다. 대화하듯 임하자.",
    "경험을 이야기로 만들 수 있는 사람이 합격한다.",
    "자신감은 준비에서 나온다.",
    "오늘 흘린 땀이 내일의 합격 통보가 된다.",
    "부족함을 아는 것이 성장의 시작이다.",
    "질문의 의도를 파악하는 것이 절반의 답이다.",
    "나만의 강점을 명확히 말할 수 있어야 한다.",
    "실전처럼 연습하고, 연습처럼 실전에 임하자.",
    "좋은 답변은 구체적인 경험에서 나온다.",
    "합격은 운이 아니라 준비의 결과다.",
    "지금 이 순간의 노력이 미래를 바꾼다.",
    "두려움은 행동으로 극복된다.",
    "피드백은 성장의 가장 빠른 길이다.",
    "남과 비교하지 말고 어제의 나와 비교하자.",
    "면접은 끝이 아니라 시작이다.",
    "성실함은 어떤 스펙보다 강력하다.",
    "한 번 더 연습하는 사람이 결국 이긴다.",
    "나의 이야기에 확신을 가지자.",
    "불합격은 방향을 알려주는 나침반이다.",
    "지금 힘든 만큼 나중에 빛날 것이다.",
    "목표가 명확하면 길은 보인다.",
    "작은 습관이 큰 결과를 만든다.",
]


@router.post("/question", response_model=QuestionResponse)
async def generate_question(req: QuestionRequest, request: Request):
    """면접 질문 생성 엔드포인트.

    직무 분야를 받아 AI가 면접 질문을 생성한다.
    과거 출제 질문을 참고하여 중복을 방지한다.
    AI 호출 실패 시 503 에러를 반환한다.
    """
    db = request.app.state.db
    ai = AIService()
    try:
        past_questions = db.get_past_questions_for_job(req.job_field, limit=5)
        question = ai.generate_question(req.job_field, past_questions)
        return QuestionResponse(question=question)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/evaluate", response_model=FeedbackResponse)
async def evaluate_answer(req: EvaluationRequest, request: Request):
    """답변 평가 엔드포인트.

    면접 질문, 답변, 직무 분야를 받아 AI가 피드백을 생성한다.
    AI 평가 성공 후에만 DB에 면접 기록을 저장한다.
    AI 호출 실패 시 503 에러를 반환하며, DB에는 저장하지 않는다.
    """
    db = request.app.state.db
    ai = AIService()

    # AI 평가 시도 - 실패 시 DB 저장 없이 503 반환
    try:
        feedback_text = ai.evaluate_answer(req.question, req.answer, req.job_field)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # AI 성공 후에만 DB 저장
    score = ai.extract_score(feedback_text)
    db.save_interview(
        job_field=req.job_field,
        question=req.question,
        answer=req.answer,
        feedback=feedback_text,
        score=score,
    )

    return FeedbackResponse(
        feedback=feedback_text,
        score=score,
        logic_score=ai.extract_section(feedback_text, "논리성"),
        keywords=ai.extract_section(feedback_text, "핵심 키워드"),
        improvements=ai.extract_section(feedback_text, "개선점"),
        summary=ai.extract_section(feedback_text, "총평"),
    )


@router.get("/daily-quote", response_model=QuoteResponse)
async def get_daily_quote():
    """오늘의 명언 엔드포인트.

    날짜 기반 시드를 사용하여 같은 날에는 동일한 명언을,
    다른 날에는 다른 명언을 반환한다.
    """
    today = date.today()
    seed = today.year * 10000 + today.month * 100 + today.day
    rng = random.Random(seed)
    return QuoteResponse(quote=rng.choice(DAILY_QUOTES))
