# -*- coding: utf-8 -*-
"""OpenRouter 클라이언트 (BYOK용).

사용자가 OpenRouter API 키를 입력하면 이 클라이언트로 라우팅된다.
한 키로 GPT-4o / Claude / Gemini 등 여러 모델 사용 가능.
"""

from __future__ import annotations

from openai import OpenAI


SYSTEM_PROMPT = (
    "너는 전문 면접관이야. 사용자가 선택한 직무에 맞는 면접 질문을 하고, "
    "답변에 대해 논리성, 핵심 키워드 포함 여부, 개선점을 구체적으로 피드백해줘. "
    "반드시 한국어로만 답변해. 한자(漢字), 중국어, 일본어, 키릴 문자 등 외국 문자를 절대 사용하지 마. "
    "한글, 영문 알파벳, 숫자, 기본 문장부호만 사용해."
)

# OpenRouter는 OpenAI 호환 endpoint
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# 사용자가 선택할 수 있는 모델 카탈로그
SUPPORTED_MODELS = {
    "anthropic/claude-sonnet-4.6": "Claude Sonnet 4.6 (균형, 추천)",
    "anthropic/claude-haiku-4.5": "Claude Haiku 4.5 (빠르고 저렴)",
    "anthropic/claude-opus-4.7": "Claude Opus 4.7 (최강 품질)",
    "openai/gpt-4o": "GPT-4o (OpenAI 최신)",
    "openai/gpt-4o-mini": "GPT-4o-mini (저렴)",
    "google/gemini-2.5-pro": "Gemini 2.5 Pro (Google)",
    "google/gemini-2.5-flash": "Gemini 2.5 Flash (빠르고 저렴)",
}

DEFAULT_MODEL = "anthropic/claude-sonnet-4.6"


class OpenRouterClient:
    """OpenRouter API를 통한 다중 LLM 호출."""

    def __init__(self, api_key: str, model: str | None = None):
        if not api_key or not api_key.strip():
            raise ValueError("OpenRouter API 키가 필요합니다.")
        self.api_key = api_key.strip()
        self.model = model or DEFAULT_MODEL
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=OPENROUTER_BASE_URL,
        )

    def generate(self, prompt: str, system: str = SYSTEM_PROMPT, max_tokens: int = 2048) -> str:
        """단일 사용자 프롬프트로 응답 생성."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            extra_headers={
                # OpenRouter가 권장하는 attribution 헤더
                "HTTP-Referer": "https://gofactory.app",
                "X-Title": "Go터뷰",
            },
        )
        return response.choices[0].message.content.strip()

    @staticmethod
    def list_models() -> dict[str, str]:
        """UI 드롭다운용 모델 카탈로그."""
        return dict(SUPPORTED_MODELS)
