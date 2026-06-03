# -*- coding: utf-8 -*-
"""회사 정보 크롤러 패키지.

Phase 2 PoC: 네이버 뉴스 + DART OpenAPI + 회사 채용 페이지에서 raw 데이터를 수집하고
LLM(Bedrock Claude)으로 요약하여 companies 테이블에 upsert.
"""

from .orchestrator import CrawlOrchestrator, CrawlResult
from .naver_news import NaverNewsCrawler
from .dart import DartCrawler, CORP_CODE_MAP
from .recruit_page import RecruitPageCrawler
from .summarizer import CompanySummarizer

__all__ = [
    "CrawlOrchestrator",
    "CrawlResult",
    "NaverNewsCrawler",
    "DartCrawler",
    "CORP_CODE_MAP",
    "RecruitPageCrawler",
    "CompanySummarizer",
]
