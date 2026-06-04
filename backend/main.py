# -*- coding: utf-8 -*-
"""FastAPI 애플리케이션 팩토리 모듈.

앱 생성, CORS 미들웨어, 라우터 등록, DB 초기화, 정적 파일 마운트,
MCP 서버 마운트를 담당한다.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.routers import health, interview, records
from backend.services.database import DatabaseService

# MCP 서버 (Claude Desktop 등 외부 LLM 클라이언트가 사용자 구독으로 호출)
try:
    from backend.mcp_server import mcp as _mcp_server

    # streamable-http transport는 자체 lifespan(session manager 시작)을 가진다.
    # 부모 FastAPI lifespan에 통합해야 /mcp 경로로 라우팅이 살아난다.
    _mcp_app = _mcp_server.http_app(path="/")
except Exception:
    _mcp_server = None
    _mcp_app = None


def create_app() -> FastAPI:
    """FastAPI 애플리케이션 인스턴스를 생성한다."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 1) DB 초기화
        db = DatabaseService(settings.database_path)
        app.state.db = db
        # 2) MCP session manager 시작 (있을 때만)
        if _mcp_app is not None:
            async with _mcp_app.lifespan(app):
                yield
        else:
            yield

    app = FastAPI(title="Go면접 API", version="1.0.0", lifespan=lifespan)

    # CORS 미들웨어 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # 프론트엔드 JS가 X-Backend-Used 응답 헤더를 읽을 수 있도록 노출
        expose_headers=["X-Backend-Used"],
    )

    # 라우터 등록 (/api 프리픽스)
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(interview.router, prefix="/api", tags=["interview"])
    app.include_router(records.router, prefix="/api", tags=["records"])

    # MCP 서버 마운트 (/mcp) — 정적 파일(/) 마운트보다 먼저 와야 함
    if _mcp_app is not None:
        app.mount("/mcp", _mcp_app)

    # 글로벌 예외 핸들러: 일관된 {"detail": "..."} 에러 형식
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "서버 내부 오류가 발생했습니다."},
        )

    # 정적 파일 마운트 (가장 마지막 — /api/* + /mcp 라우트가 우선 처리됨)
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
