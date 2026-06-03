# -*- coding: utf-8 -*-
"""OpenRouter BYOK 키 검증 모듈.

사용자가 입력한 OpenRouter API 키에 대해 두 가지 검증을 수행한다:

1. 형식 검증: ``sk-or-v1-`` 접두어 + 충분한 길이 확인 (로컬, 무비용)
2. 실제 검증: OpenRouter ``/auth/key`` 엔드포인트 호출로 발급 여부·잔액 확인

보안:
    - 키 원문은 로그·DB·응답 본문 어디에도 기록하지 않는다.
    - 디버그가 필요한 경우 :func:`mask_key` 결과만 사용한다.
    - 이 모듈은 키를 인메모리에서만 다룬다 (요청 처리 중 한정).
"""

from __future__ import annotations

from typing import Any

import httpx


# OpenRouter 키 형식: sk-or-v1-<64자 hex>
OPENROUTER_KEY_PREFIX = "sk-or-v1-"
OPENROUTER_MIN_KEY_LENGTH = 40
OPENROUTER_AUTH_URL = "https://openrouter.ai/api/v1/auth/key"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

# 검증 타임아웃 (초). 너무 길면 UX 저하, 너무 짧으면 false negative
_VALIDATE_TIMEOUT_SEC = 8.0


def is_well_formed(api_key: str | None) -> bool:
    """OpenRouter 키 형식 검증 (네트워크 호출 없음).

    Args:
        api_key: 검증할 API 키 문자열 (None/빈 문자열 허용).

    Returns:
        형식이 올바르면 True, 아니면 False.
    """
    if not api_key:
        return False
    key = api_key.strip()
    if not key.startswith(OPENROUTER_KEY_PREFIX):
        return False
    if len(key) < OPENROUTER_MIN_KEY_LENGTH:
        return False
    return True


def mask_key(api_key: str | None) -> str:
    """로깅/디버그용 키 마스킹.

    예) "sk-or-v1-abcdef...wxyz" 형태로 앞 prefix + 뒤 4자리만 노출.

    Args:
        api_key: 마스킹할 API 키.

    Returns:
        마스킹된 문자열. 키가 비었으면 ``"(none)"``.
    """
    if not api_key:
        return "(none)"
    key = api_key.strip()
    if len(key) <= len(OPENROUTER_KEY_PREFIX) + 4:
        return "(invalid)"
    tail = key[-4:]
    return f"{OPENROUTER_KEY_PREFIX}...{tail}"


def _empty_result(error: str | None = None) -> dict[str, Any]:
    """검증 실패 시 반환할 기본 결과 dict."""
    return {
        "valid": False,
        "label": None,
        "credit_left": None,
        "models_count": None,
        "error": error,
    }


def validate_openrouter_key(api_key: str | None) -> dict[str, Any]:
    """OpenRouter 키 검증 (형식 + 실제 호출).

    OpenRouter의 ``GET /auth/key`` 엔드포인트는 다음과 같은 응답을 준다
    (스키마는 공식 문서 기준; 변경 가능):

    .. code-block:: json

        {
          "data": {
            "label": "key-label",
            "usage": 1.23,
            "limit": 10.0,
            "is_free_tier": false,
            "rate_limit": {"requests": 100, "interval": "10s"}
          }
        }

    Args:
        api_key: 사용자가 입력한 OpenRouter API 키.

    Returns:
        dict with keys:

        - ``valid`` (bool): 키가 유효한지
        - ``label`` (str | None): 키 라벨 (사용자 식별용)
        - ``credit_left`` (float | None): 잔액 (limit - usage)
        - ``models_count`` (int | None): 접근 가능한 모델 수
        - ``error`` (str | None): 에러 메시지 (사용자 표시용, 키 미포함)
    """
    # 1) 형식 체크
    if not is_well_formed(api_key):
        return _empty_result(
            error="키 형식이 올바르지 않습니다. 'sk-or-v1-'로 시작하는 키를 입력하세요."
        )

    key = api_key.strip()
    headers = {
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "https://gofactory.app",
        "X-Title": "Go터뷰",
    }

    # 2) /auth/key 호출
    try:
        with httpx.Client(timeout=_VALIDATE_TIMEOUT_SEC) as client:
            resp = client.get(OPENROUTER_AUTH_URL, headers=headers)
    except httpx.TimeoutException:
        return _empty_result(error="OpenRouter 응답이 지연되었습니다. 잠시 후 다시 시도하세요.")
    except httpx.HTTPError as exc:
        return _empty_result(error=f"네트워크 오류: {type(exc).__name__}")

    if resp.status_code == 401:
        return _empty_result(error="키가 유효하지 않습니다 (401 Unauthorized).")
    if resp.status_code == 403:
        return _empty_result(error="키 권한이 부족합니다 (403 Forbidden).")
    if resp.status_code >= 400:
        return _empty_result(
            error=f"OpenRouter 검증 실패 (HTTP {resp.status_code})."
        )

    try:
        payload = resp.json()
    except ValueError:
        return _empty_result(error="OpenRouter 응답을 해석할 수 없습니다.")

    data = payload.get("data") or {}
    label = data.get("label")
    usage = _safe_float(data.get("usage"))
    limit = _safe_float(data.get("limit"))

    credit_left: float | None = None
    if limit is not None and usage is not None:
        credit_left = max(limit - usage, 0.0)
    elif data.get("is_free_tier") is True:
        # 무료 티어 키의 경우 limit이 없을 수 있음
        credit_left = None

    # 3) 모델 개수 (best-effort: 실패해도 valid=True 유지)
    models_count = _count_available_models(key)

    return {
        "valid": True,
        "label": label,
        "credit_left": credit_left,
        "models_count": models_count,
        "error": None,
    }


def _safe_float(value: Any) -> float | None:
    """JSON 응답 값을 float로 안전 변환."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _count_available_models(api_key: str) -> int | None:
    """OpenRouter에서 키로 접근 가능한 모델 수 조회.

    실패해도 None을 반환하여 검증 흐름을 막지 않는다.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://gofactory.app",
        "X-Title": "Go터뷰",
    }
    try:
        with httpx.Client(timeout=_VALIDATE_TIMEOUT_SEC) as client:
            resp = client.get(OPENROUTER_MODELS_URL, headers=headers)
        if resp.status_code != 200:
            return None
        body = resp.json()
        models = body.get("data") or []
        return len(models) if isinstance(models, list) else None
    except (httpx.HTTPError, ValueError):
        return None
