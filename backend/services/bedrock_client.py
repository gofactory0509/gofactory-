# -*- coding: utf-8 -*-
"""AWS Bedrock 클라이언트 (Anthropic Claude Sonnet 4.6 기본).

사용자가 OpenRouter BYOK 키를 입력하지 않은 경우 이 클라이언트가 사용된다.
EC2 인스턴스 IAM Role을 통해 Bedrock 인증.
"""

from __future__ import annotations

import os

from anthropic import AnthropicBedrock


SYSTEM_PROMPT = (
    "너는 전문 면접관이야. 사용자가 선택한 직무에 맞는 면접 질문을 하고, "
    "답변에 대해 논리성, 핵심 키워드 포함 여부, 개선점을 구체적으로 피드백해줘. "
    "반드시 한국어로만 답변해. 한자(漢字), 중국어, 일본어, 키릴 문자 등 외국 문자를 절대 사용하지 마. "
    "한글, 영문 알파벳, 숫자, 기본 문장부호만 사용해."
)


class BedrockClient:
    """AWS Bedrock에서 Anthropic Claude 모델 호출.

    환경 변수:
        AWS_REGION: Bedrock region (기본 us-east-1)
        BEDROCK_MODEL_ID: 사용할 모델 ID
            (예: anthropic.claude-sonnet-4-6-20251015-v1:0)
    """

    def __init__(self, region: str | None = None, model_id: str | None = None):
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.model_id = model_id or os.getenv(
            "BEDROCK_MODEL_ID",
            "anthropic.claude-sonnet-4-6-20251015-v1:0",
        )
        # EC2 IAM Role 사용 시 credentials 자동 주입
        self.client = AnthropicBedrock(aws_region=self.region)

    def generate(self, prompt: str, system: str = SYSTEM_PROMPT, max_tokens: int = 2048) -> str:
        """단일 사용자 프롬프트로 응답 생성."""
        message = self.client.messages.create(
            model=self.model_id,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        # Anthropic messages API는 content가 블록 리스트
        if message.content and len(message.content) > 0:
            return message.content[0].text.strip()
        return ""

    def is_available(self) -> bool:
        """Bedrock 인증·모델 접근 가능 여부 (lightweight check)."""
        try:
            self.client.messages.create(
                model=self.model_id,
                max_tokens=8,
                system="응답: ok",
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False
