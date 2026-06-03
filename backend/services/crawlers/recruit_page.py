# -*- coding: utf-8 -*-
"""회사 채용 페이지 스크래퍼.

BeautifulSoup으로 채용 페이지의 인재상/회사소개 텍스트를 추출.
selector는 회사마다 다르므로 휴리스틱(주요 텍스트 블록 추출) 사용.
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


DEFAULT_TIMEOUT = 15  # seconds
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
)

# 인재상 키워드 — 휴리스틱으로 관련 섹션 우선 추출
TALENT_KEYWORDS = (
    "인재상", "인재", "Talent", "Vision", "비전", "핵심가치", "Core Value",
    "Way", "철학", "Philosophy", "People", "We Are",
)

# 검증되지 않은 가정: 회사별 인재상 영역 selector
# 실제 페이지가 SPA(JS 렌더링)면 BeautifulSoup만으로는 안 잡힘 → Playwright 필요
COMPANY_SELECTORS: dict[str, list[str]] = {
    "삼성전자": ["section", "div.talent", "div.vision", "main"],
    "SK하이닉스": ["section", "div.talent", "div.vision", "main"],
    "DB하이텍": ["section", "div.about", "main"],
    "한미반도체": ["section", "div.about", "div.vision", "main"],
    "솔브레인": ["section", "div.about", "div.talent", "main"],
}


class RecruitPageCrawler:
    """회사 채용/소개 페이지에서 인재상 텍스트 추출."""

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
        max_chars: int = 3000,
    ):
        self.timeout = timeout
        self.user_agent = user_agent
        self.max_chars = max_chars

    def fetch(self, company_name: str, url: str) -> dict[str, Any]:
        """URL에서 텍스트 추출.

        Returns:
            dict: {"source": "recruit_page", "company": str, "url": str,
                   "raw_text": str, "talent_text": str}
        """
        if not url:
            return self._empty(company_name, url)

        try:
            response = requests.get(
                url,
                headers={"User-Agent": self.user_agent, "Accept-Language": "ko-KR,ko;q=0.9"},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("RecruitPageCrawler: fetch failed (%s, %s): %s", company_name, url, exc)
            return self._empty(company_name, url)

        # 인코딩 추정 보정
        if not response.encoding or response.encoding.lower() == "iso-8859-1":
            response.encoding = response.apparent_encoding or "utf-8"

        try:
            soup = BeautifulSoup(response.text, "lxml")
        except Exception:
            # lxml 미설치 시 fallback
            soup = BeautifulSoup(response.text, "html.parser")

        # script, style 제거
        for tag in soup(["script", "style", "noscript", "iframe"]):
            tag.decompose()

        # 전체 텍스트
        full_text = self._clean_text(soup.get_text(separator="\n"))
        raw_text = full_text[: self.max_chars]

        # 인재상 관련 영역 추출 (휴리스틱)
        talent_text = self._extract_talent_section(soup, company_name)

        return {
            "source": "recruit_page",
            "company": company_name,
            "url": url,
            "raw_text": raw_text,
            "talent_text": talent_text,
        }

    def _extract_talent_section(self, soup: BeautifulSoup, company_name: str) -> str:
        """인재상 키워드가 포함된 블록을 우선 추출."""
        # 1) 키워드 헤딩(h1~h4) 주변 텍스트 우선
        candidates: list[str] = []
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "strong", "b"]):
            text = tag.get_text(strip=True)
            if not text:
                continue
            if any(kw in text for kw in TALENT_KEYWORDS):
                # 헤딩 부모 또는 다음 형제까지 텍스트 수집
                parent = tag.find_parent(["section", "div", "article"]) or tag.parent
                if parent:
                    block_text = self._clean_text(parent.get_text(separator=" "))
                    if len(block_text) > 30:
                        candidates.append(block_text[: self.max_chars])

        if candidates:
            # 가장 긴 후보 반환
            return max(candidates, key=len)[: self.max_chars]

        # 2) 회사별 selector fallback
        for sel in COMPANY_SELECTORS.get(company_name, ["main", "section"]):
            try:
                el = soup.select_one(sel)
            except Exception:
                continue
            if el:
                text = self._clean_text(el.get_text(separator=" "))
                if len(text) > 100:
                    return text[: self.max_chars]
        return ""

    @staticmethod
    def _empty(company_name: str, url: str) -> dict[str, Any]:
        return {
            "source": "recruit_page",
            "company": company_name,
            "url": url,
            "raw_text": "",
            "talent_text": "",
        }

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        # 공백 정리
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]
        return "\n".join(lines)
