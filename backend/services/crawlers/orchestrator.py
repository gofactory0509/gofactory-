# -*- coding: utf-8 -*-
"""크롤링 → 요약 → DB upsert 흐름을 통합하는 오케스트레이터.

회사별로 3개 소스(naver/dart/recruit)에서 raw 데이터를 수집하고,
CompanySummarizer로 요약한 뒤 InterviewDB.upsert_company_info로 저장한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterable

from .dart import DartCrawler
from .naver_news import NaverNewsCrawler
from .recruit_page import RecruitPageCrawler
from .summarizer import CompanySummarizer


logger = logging.getLogger(__name__)


VALID_SOURCES = ("naver", "dart", "recruit")


@dataclass
class CrawlResult:
    """회사 한 곳에 대한 크롤링 결과."""

    company: str
    success: bool = False
    sources_ok: list[str] = field(default_factory=list)
    sources_failed: list[str] = field(default_factory=list)
    info: dict[str, Any] = field(default_factory=dict)  # upsert에 들어간 dict
    error: str | None = None
    db_id: int | None = None

    def short(self) -> str:
        return (
            f"{self.company}: success={self.success} "
            f"ok={','.join(self.sources_ok) or '-'} "
            f"failed={','.join(self.sources_failed) or '-'}"
        )


class CrawlOrchestrator:
    """회사별 raw 수집 + LLM 요약 + DB upsert를 묶는 facade.

    db: InterviewDB 인스턴스. dry_run=True면 upsert_company_info 호출 안 함.
    seeds: COMPANY_SEEDS 리스트 (name, aliases, source_urls 등).
    """

    def __init__(
        self,
        db: Any,
        seeds: list[dict],
        naver: NaverNewsCrawler | None = None,
        dart: DartCrawler | None = None,
        recruit: RecruitPageCrawler | None = None,
        summarizer: CompanySummarizer | None = None,
        sources: Iterable[str] = VALID_SOURCES,
        dry_run: bool = False,
    ):
        self.db = db
        self.seeds_by_name = {seed["name"]: seed for seed in seeds}
        self.naver = naver or NaverNewsCrawler()
        self.dart = dart or DartCrawler()
        self.recruit = recruit or RecruitPageCrawler()
        self.summarizer = summarizer or CompanySummarizer(bedrock_client=None)
        self.sources = tuple(s for s in sources if s in VALID_SOURCES)
        self.dry_run = dry_run

    def crawl_company(self, company_name: str) -> CrawlResult:
        """단일 회사 처리."""
        result = CrawlResult(company=company_name)
        seed = self.seeds_by_name.get(company_name)
        if not seed:
            result.error = f"unknown company (not in seeds): {company_name}"
            logger.warning(result.error)
            return result

        # 1) raw 수집
        naver_data = self._safe_fetch_naver(company_name, result) if "naver" in self.sources else None
        dart_data = self._safe_fetch_dart(company_name, result) if "dart" in self.sources else None
        recruit_data = (
            self._safe_fetch_recruit(company_name, seed.get("source_urls", ""), result)
            if "recruit" in self.sources
            else None
        )

        # 2) LLM 요약
        recruit_raw = (recruit_data or {}).get("talent_text", "") or (recruit_data or {}).get("raw_text", "")
        news_raw = (naver_data or {}).get("raw_text", "")
        dart_raw = (dart_data or {}).get("raw_text", "")

        try:
            talent_summary = self.summarizer.summarize_talent(
                company_name, recruit_raw, seed_text=seed.get("talent_profile", "")
            )
        except Exception as exc:
            logger.warning("summarize_talent failed for %s: %s", company_name, exc)
            talent_summary = seed.get("talent_profile", "")

        try:
            trend_summary = self.summarizer.summarize_recent_trend(
                company_name,
                news_raw,
                dart_text=dart_raw,
                seed_text=seed.get("recent_news_summary", ""),
            )
        except Exception as exc:
            logger.warning("summarize_recent_trend failed for %s: %s", company_name, exc)
            trend_summary = seed.get("recent_news_summary", "")

        try:
            business_summary = self.summarizer.summarize_business_focus(
                company_name, dart_text=dart_raw, seed_text=seed.get("business_focus", "")
            )
        except Exception as exc:
            logger.warning("summarize_business_focus failed for %s: %s", company_name, exc)
            business_summary = seed.get("business_focus", "")

        # 3) DB upsert 페이로드
        info = {
            "name": seed["name"],
            "aliases": seed.get("aliases", ""),
            "industry": seed.get("industry", ""),
            "talent_profile": talent_summary or seed.get("talent_profile", ""),
            "business_focus": business_summary or seed.get("business_focus", ""),
            "recent_news_summary": trend_summary or seed.get("recent_news_summary", ""),
            "recruiting_status": seed.get("recruiting_status", ""),
            "source_urls": seed.get("source_urls", ""),
            "is_cached": True,
        }
        result.info = info

        # 모든 소스가 실패했고 raw가 전혀 없으면 실패로 처리(시드만 있는 상태)
        if not self.sources_yielded_data(naver_data, dart_data, recruit_data):
            result.error = "all sources returned no data"
            logger.warning("Crawl[%s]: all sources empty", company_name)
            # 그래도 시드 기반 upsert는 가능 → success=False지만 db 반영은 dry_run 외에는 수행
        else:
            result.success = True

        if not self.dry_run:
            try:
                result.db_id = self.db.upsert_company_info(info)
            except Exception as exc:
                logger.error("DB upsert failed for %s: %s", company_name, exc)
                result.error = f"db_upsert_failed: {exc}"
                result.success = False

        return result

    @staticmethod
    def sources_yielded_data(*payloads: dict | None) -> bool:
        for p in payloads:
            if not p:
                continue
            if p.get("raw_text") or p.get("items") or p.get("talent_text") or p.get("disclosures"):
                return True
        return False

    def crawl_many(self, companies: list[str]) -> list[CrawlResult]:
        results: list[CrawlResult] = []
        for name in companies:
            try:
                results.append(self.crawl_company(name))
            except Exception as exc:
                logger.error("crawl_company crashed for %s: %s", name, exc, exc_info=True)
                results.append(
                    CrawlResult(company=name, success=False, error=f"crash: {exc}")
                )
        return results

    # ── 개별 소스 안전 호출 ──

    def _safe_fetch_naver(self, company_name: str, result: CrawlResult) -> dict | None:
        try:
            data = self.naver.fetch(company_name)
            if data.get("items"):
                result.sources_ok.append("naver")
            else:
                result.sources_failed.append("naver")
            return data
        except Exception as exc:
            logger.warning("naver fetch failed for %s: %s", company_name, exc)
            result.sources_failed.append("naver")
            return None

    def _safe_fetch_dart(self, company_name: str, result: CrawlResult) -> dict | None:
        try:
            data = self.dart.fetch(company_name)
            if data.get("company_info") or data.get("disclosures"):
                result.sources_ok.append("dart")
            else:
                result.sources_failed.append("dart")
            return data
        except Exception as exc:
            logger.warning("dart fetch failed for %s: %s", company_name, exc)
            result.sources_failed.append("dart")
            return None

    def _safe_fetch_recruit(
        self, company_name: str, url: str, result: CrawlResult
    ) -> dict | None:
        try:
            data = self.recruit.fetch(company_name, url)
            if data.get("raw_text") or data.get("talent_text"):
                result.sources_ok.append("recruit")
            else:
                result.sources_failed.append("recruit")
            return data
        except Exception as exc:
            logger.warning("recruit fetch failed for %s: %s", company_name, exc)
            result.sources_failed.append("recruit")
            return None
