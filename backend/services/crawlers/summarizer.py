# -*- coding: utf-8 -*-
"""LLM(Bedrock Claude) 기반 회사 정보 요약기.

채용 페이지·뉴스·DART raw 데이터를 받아 한국어 요약을 생성.
AWS credentials/Bedrock 접근 불가 시 raw 텍스트 truncate로 fallback.
"""

from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "너는 한국 반도체 기업 정보를 정리하는 요약 전문가야. "
    "응답은 반드시 한국어로만 작성하고, 한자(漢字)·중국어·일본어·키릴 등 외국 문자를 사용하지 마. "
    "한글, 영문 알파벳(회사명·기술명에 한해), 숫자, 기본 문장부호만 사용해. "
    "사실 위주로 요약하고 추측하지 마. 모르면 모른다고 적어."
)


# raw fallback 시 잘라낼 문자 수
RAW_TRUNCATE = 100


class CompanySummarizer:
    """LLM으로 raw 데이터를 가공된 요약으로 변환.

    bedrock_client는 generate(prompt, system, max_tokens) 메서드만 있으면 됨 → 테스트시 stub 가능.
    """

    def __init__(self, bedrock_client: Any | None = None):
        """
        Args:
            bedrock_client: BedrockClient 인스턴스. None이면 fallback 모드(raw truncate).
        """
        self.client = bedrock_client

    @property
    def is_available(self) -> bool:
        return self.client is not None

    def summarize_talent(self, company_name: str, recruit_text: str, seed_text: str = "") -> str:
        """인재상 요약 (목표 200자 한국어)."""
        combined = (seed_text + "\n" + recruit_text).strip()
        if not combined:
            return seed_text or ""

        if not self.is_available:
            return self._fallback(combined)

        prompt = (
            f"[회사] {company_name}\n"
            f"[채용 페이지/회사소개 원문 발췌]\n{recruit_text[:2000]}\n\n"
            f"[참고용 기존 인재상 설명(있으면)]\n{seed_text}\n\n"
            "위 자료를 바탕으로 이 회사의 인재상을 약 200자 한국어로 정리해줘. "
            "가치관·인재 우선순위·핵심 역량 키워드 중심으로 작성하고, "
            "한자/외국 문자 금지, 사실 위주, 추측 금지."
        )
        return self._call(prompt, max_tokens=400) or self._fallback(combined)

    def summarize_recent_trend(
        self,
        company_name: str,
        news_text: str,
        dart_text: str = "",
        seed_text: str = "",
    ) -> str:
        """최근 트렌드/뉴스 요약 (목표 300자 한국어)."""
        combined = "\n".join(t for t in (news_text, dart_text, seed_text) if t).strip()
        if not combined:
            return seed_text or ""

        if not self.is_available:
            return self._fallback(combined)

        prompt = (
            f"[회사] {company_name}\n"
            f"[네이버 뉴스 헤드라인/요약]\n{news_text[:2500]}\n\n"
            f"[DART 공시 요약]\n{dart_text[:1500]}\n\n"
            f"[참고용 기존 트렌드 설명(있으면)]\n{seed_text}\n\n"
            "위 자료를 바탕으로 이 회사의 최근 트렌드(사업·기술·실적·시장)를 약 300자 한국어로 정리해줘. "
            "한자/외국 문자 금지, 사실 위주, 추측 금지. 중요한 숫자/제품명/계약은 포함."
        )
        return self._call(prompt, max_tokens=600) or self._fallback(combined)

    def summarize_business_focus(
        self, company_name: str, dart_text: str = "", seed_text: str = ""
    ) -> str:
        """주력 사업 요약 (목표 100자 한국어)."""
        combined = "\n".join(t for t in (dart_text, seed_text) if t).strip()
        if not combined:
            return seed_text or ""

        if not self.is_available:
            return self._fallback(combined)

        prompt = (
            f"[회사] {company_name}\n"
            f"[DART 기업개황/업종]\n{dart_text[:1500]}\n\n"
            f"[참고용 기존 주력사업 설명(있으면)]\n{seed_text}\n\n"
            "위 자료를 바탕으로 이 회사의 주력 사업을 약 100자 한국어로 정리해줘. "
            "주력 제품군·기술 키워드 중심. 한자/외국 문자 금지, 사실 위주, 추측 금지."
        )
        return self._call(prompt, max_tokens=300) or self._fallback(combined)

    def _call(self, prompt: str, max_tokens: int) -> str:
        try:
            return self.client.generate(prompt, system=SYSTEM_PROMPT, max_tokens=max_tokens).strip()
        except Exception as exc:
            logger.warning("CompanySummarizer LLM call failed: %s", exc)
            return ""

    @staticmethod
    def _fallback(raw: str) -> str:
        """LLM 사용 불가 시 raw 데이터를 RAW_TRUNCATE자로 잘라 반환."""
        if not raw:
            return ""
        text = raw.replace("\n", " ").strip()
        if len(text) <= RAW_TRUNCATE:
            return text
        return text[:RAW_TRUNCATE] + "..."
