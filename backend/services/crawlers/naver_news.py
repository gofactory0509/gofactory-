# -*- coding: utf-8 -*-
"""네이버 뉴스 검색 API 크롤러.

환경변수:
    NAVER_CLIENT_ID, NAVER_CLIENT_SECRET — 네이버 개발자센터 발급
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

import requests


logger = logging.getLogger(__name__)

NAVER_NEWS_ENDPOINT = "https://openapi.naver.com/v1/search/news.json"
DEFAULT_DISPLAY = 10  # 회사당 가져올 뉴스 개수
DEFAULT_TIMEOUT = 10  # seconds


class NaverNewsCrawler:
    """네이버 뉴스 검색 API 래퍼.

    회사명으로 검색하여 최근 뉴스 헤드라인과 요약(description)을 수집.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        display: int = DEFAULT_DISPLAY,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.client_id = client_id or os.getenv("NAVER_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("NAVER_CLIENT_SECRET", "")
        self.display = display
        self.timeout = timeout

    def is_configured(self) -> bool:
        """NAVER_CLIENT_ID/SECRET 둘 다 설정되어 있는지."""
        return bool(self.client_id) and bool(self.client_secret)

    def fetch(self, company_name: str) -> dict[str, Any]:
        """회사명으로 네이버 뉴스 검색.

        Returns:
            dict: {"source": "naver_news", "company": str, "items": list[dict], "raw_text": str}
                items 각 항목: {title, link, description, pub_date}
                raw_text: 요약/저장용으로 합친 텍스트
        """
        if not self.is_configured():
            logger.warning("NaverNewsCrawler: NAVER_CLIENT_ID/SECRET not set, skipping")
            return self._empty(company_name)

        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }
        params = {
            "query": company_name,
            "display": self.display,
            "sort": "date",  # 최신순
        }
        try:
            response = requests.get(
                NAVER_NEWS_ENDPOINT,
                headers=headers,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("NaverNewsCrawler: fetch failed for %s: %s", company_name, exc)
            return self._empty(company_name)

        items = []
        for raw in data.get("items", []):
            items.append(
                {
                    "title": _strip_html(raw.get("title", "")),
                    "link": raw.get("link", ""),
                    "description": _strip_html(raw.get("description", "")),
                    "pub_date": raw.get("pubDate", ""),
                }
            )

        raw_text = self._build_raw_text(items)
        return {
            "source": "naver_news",
            "company": company_name,
            "items": items,
            "raw_text": raw_text,
        }

    @staticmethod
    def _empty(company_name: str) -> dict[str, Any]:
        return {
            "source": "naver_news",
            "company": company_name,
            "items": [],
            "raw_text": "",
        }

    @staticmethod
    def _build_raw_text(items: list[dict]) -> str:
        """뉴스 항목들을 LLM 입력용 단일 텍스트로 합침."""
        lines: list[str] = []
        for idx, item in enumerate(items, start=1):
            title = item.get("title", "")
            desc = item.get("description", "")
            lines.append(f"{idx}. {title} — {desc}")
        return "\n".join(lines)


_TAG_RE = re.compile(r"<[^>]+>")
_ENTITY_MAP = {
    "&quot;": '"',
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&apos;": "'",
    "&#39;": "'",
    "&nbsp;": " ",
}


def _strip_html(text: str) -> str:
    """네이버 응답의 <b> 태그·HTML 엔티티 정리."""
    if not text:
        return ""
    cleaned = _TAG_RE.sub("", text)
    for entity, char in _ENTITY_MAP.items():
        cleaned = cleaned.replace(entity, char)
    return cleaned.strip()
