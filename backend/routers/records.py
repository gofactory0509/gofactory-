"""면접 기록 및 통계 라우터.

면접 기록 조회(직무별 필터링 포함)와 통계 엔드포인트를 제공한다.
"""

from fastapi import APIRouter, Query, Request

from backend.models import InterviewRecord, RecordsResponse, StatsResponse

router = APIRouter()


@router.get("/records", response_model=RecordsResponse)
async def get_records(
    request: Request,
    job_field: str | None = Query(None, description="직무별 필터"),
):
    """면접 기록 조회.

    전체 기록을 날짜 내림차순으로 반환한다.
    job_field 쿼리 파라미터가 주어지면 해당 직무의 기록만 필터링한다.
    """
    db = request.app.state.db
    if job_field:
        records = db.get_records_by_job(job_field)
    else:
        records = db.get_all_records()
    return RecordsResponse(records=[InterviewRecord(**r) for r in records])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(request: Request):
    """면접 통계 조회.

    총 면접 횟수, 평균 점수, 최다 연습 직무, 직무별 분포, 질문 뱅크 크기를 반환한다.
    """
    db = request.app.state.db
    stats = db.get_stats()
    return StatsResponse(**stats)
