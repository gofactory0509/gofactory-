# -*- coding: utf-8 -*-
"""FastAPI 애플리케이션 팩토리 모듈.

앱 생성, CORS 미들웨어, 라우터 등록, DB 초기화, 정적 파일 마운트를 담당한다.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.routers import health, interview, records
from backend.services.database import DatabaseService


def create_app() -> FastAPI:
    """FastAPI 애플리케이션 인스턴스를 생성한다.

    Returns:
        설정이 완료된 FastAPI 앱 인스턴스
    """
    app = FastAPI(title="Go면접 API", version="1.0.0")

    # CORS 미들웨어 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록 (/api 프리픽스)
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(interview.router, prefix="/api", tags=["interview"])
    app.include_router(records.router, prefix="/api", tags=["records"])

    # 글로벌 예외 핸들러: 일관된 {"detail": "..."} 에러 형식
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "서버 내부 오류가 발생했습니다."},
        )

    # DB 초기화 (startup 이벤트)
    @app.on_event("startup")
    async def startup() -> None:
        db = DatabaseService(settings.database_path)
        app.state.db = db

    # 정적 파일 마운트 (가장 마지막 — /api/* 라우트가 우선 처리됨)
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
