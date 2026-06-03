# -*- coding: utf-8 -*-
"""BYOK (Bring Your Own Key) 라우터.

사용자가 자신의 OpenRouter API 키를 시스템에 제공할 때 그 키의 유효성을
검증하고, 선택 가능한 모델 카탈로그를 노출한다.

엔드포인트:
    - ``POST /api/byok/validate`` : 키 유효성 검증
    - ``GET  /api/byok/models``   : 지원 모델 카탈로그 조회

보안 원칙:
    - 키 자체는 응답 본문에 절대 포함하지 않는다.
    - 로깅 시 :func:`backend.services.key_validator.mask_key` 를 거친 마스킹 값만 사용.
    - 키는 헤더 ``X-OpenRouter-Key`` 또는 요청 바디에서만 수신하며 저장하지 않는다.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from backend.services.key_validator import (
    mask_key,
    validate_openrouter_key,
)
from backend.services.openrouter_client import (
    DEFAULT_MODEL,
    OpenRouterClient,
)


router = APIRouter(prefix="/byok", tags=["byok"])


# ─── Schemas ───


class ValidateRequest(BaseModel):
    """키 검증 요청 (헤더 미사용 시 폴백)."""

    api_key: Optional[str] = Field(
        default=None,
        description=(
            "OpenRouter API 키. 헤더 ``X-OpenRouter-Key`` 사용을 권장하며, "
            "본 바디는 호환성용 폴백이다."
        ),
    )


class ValidateResponse(BaseModel):
    """키 검증 응답.

    Attributes:
        valid: 키 유효 여부.
        label: 키 라벨 (사용자 식별용; OpenRouter 콘솔에서 부여한 이름).
        credit_left: 잔액 (USD; 무료 티어는 None일 수 있음).
        models_count: 키로 접근 가능한 모델 수.
        error: 사용자 표시용 에러 메시지 (키 정보 미포함).
        key_preview: 마스킹된 키 미리보기 (예: ``sk-or-v1-...ab12``).
    """

    valid: bool
    label: str | None = None
    credit_left: float | None = None
    models_count: int | None = None
    error: str | None = None
    key_preview: str | None = None


class ModelsResponse(BaseModel):
    """모델 카탈로그 응답."""

    default: str
    models: dict[str, str]


# ─── Endpoints ───


@router.post("/validate", response_model=ValidateResponse)
async def validate_key(
    body: ValidateRequest | None = None,
    x_openrouter_key: str | None = Header(None, alias="X-OpenRouter-Key"),
) -> ValidateResponse:
    """OpenRouter API 키 검증.

    헤더 ``X-OpenRouter-Key`` 우선, 없으면 요청 바디의 ``api_key`` 사용.
    검증 결과만 응답하며 키 원문은 절대 포함하지 않는다.

    Args:
        body: 선택적 요청 바디 (키를 헤더로 못 보낼 때 폴백).
        x_openrouter_key: 헤더로 받은 키 (권장).

    Returns:
        :class:`ValidateResponse` — 유효성 + 잔액/라벨 + 마스킹된 미리보기.
    """
    api_key = x_openrouter_key or (body.api_key if body else None)
    result = validate_openrouter_key(api_key)
    return ValidateResponse(
        valid=result["valid"],
        label=result.get("label"),
        credit_left=result.get("credit_left"),
        models_count=result.get("models_count"),
        error=result.get("error"),
        key_preview=mask_key(api_key) if api_key else None,
    )


@router.get("/models", response_model=ModelsResponse)
async def list_models() -> ModelsResponse:
    """지원 모델 카탈로그 반환.

    프론트엔드 드롭다운/Streamlit selectbox 채우기에 사용한다.
    이 엔드포인트는 인증이 필요하지 않다.

    Returns:
        :class:`ModelsResponse` — 기본 모델 ID + 지원 모델 dict.
    """
    return ModelsResponse(
        default=DEFAULT_MODEL,
        models=OpenRouterClient.list_models(),
    )
