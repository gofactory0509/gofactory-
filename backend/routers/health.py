"""헬스체크 라우터.

서버 상태 확인을 위한 엔드포인트를 제공한다.
"""

from datetime import datetime

from fastapi import APIRouter

from backend.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """서버 상태 및 현재 타임스탬프를 반환한다."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.now().isoformat(),
    )
