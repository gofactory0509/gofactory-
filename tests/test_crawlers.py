# -*- coding: utf-8 -*-
"""회사 정보 크롤러 단위 테스트.

외부 API 호출은 unittest.mock으로 stub. 통합 테스트는 @pytest.mark.live (기본 skip).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 프로젝트 루트 import path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.crawlers.dart import DartCrawler, CORP_CODE_MAP
from backend.services.crawlers.naver_news import NaverNewsCrawler, _strip_html
from backend.services.crawlers.orchestrator import CrawlOrchestrator, CrawlResult
from backend.services.crawlers.recruit_page import RecruitPageCrawler
from backend.services.crawlers.summarizer import CompanySummarizer


SAMPLE_SEEDS = [
    {
        "name": "삼성전자",
        "aliases": "Samsung, SEC",
        "industry": "반도체-IDM",
        "talent_profile": "도전 의식과 창의력으로 변화를 선도",
        "business_focus": "DRAM, NAND, HBM, Foundry",
        "recent_news_summary": "HBM4 양산 본격화",
        "recruiting_status": "2026 상반기 약 1000명",
        "source_urls": "https://www.samsung-dsrecruit.com/",
    },
    {
        "name": "SK하이닉스",
        "aliases": "Hynix",
        "industry": "반도체-IDM",
        "talent_profile": "SUPEX 수준 도전 정신",
        "business_focus": "DRAM, NAND, HBM",
        "recent_news_summary": "HBM 글로벌 1위",
        "recruiting_status": "채용 확대",
        "source_urls": "https://recruit.skhynix.com/",
    },
]


# ───────────── NaverNewsCrawler ─────────────


class TestNaverNewsCrawler:
    def test_not_configured_returns_empty(self):
        crawler = NaverNewsCrawler(client_id="", client_secret="")
        assert crawler.is_configured() is False
        result = crawler.fetch("삼성전자")
        assert result["items"] == []
        assert result["raw_text"] == ""
        assert result["company"] == "삼성전자"

    def test_fetch_parses_response(self):
        crawler = NaverNewsCrawler(client_id="id", client_secret="secret")
        fake_response = MagicMock()
        fake_response.json.return_value = {
            "items": [
                {
                    "title": "<b>삼성전자</b>, HBM4 공급 확대",
                    "link": "https://news.example.com/1",
                    "description": "HBM4 양산이 본격화&quot;되었다&quot;",
                    "pubDate": "Mon, 02 Jun 2026 09:00:00 +0900",
                },
                {
                    "title": "삼성 파운드리 2nm 공정 진척",
                    "link": "https://news.example.com/2",
                    "description": "TSMC 추격",
                    "pubDate": "Mon, 02 Jun 2026 08:00:00 +0900",
                },
            ]
        }
        fake_response.raise_for_status = MagicMock()

        with patch("backend.services.crawlers.naver_news.requests.get", return_value=fake_response) as mocked:
            result = crawler.fetch("삼성전자")

        mocked.assert_called_once()
        assert len(result["items"]) == 2
        # HTML 태그 제거 확인
        assert "<b>" not in result["items"][0]["title"]
        assert "삼성전자" in result["items"][0]["title"]
        # 엔티티 변환
        assert "&quot;" not in result["items"][0]["description"]
        # raw_text 빌드
        assert "1." in result["raw_text"]
        assert "HBM4" in result["raw_text"]

    def test_fetch_handles_http_error(self):
        import requests as _r

        crawler = NaverNewsCrawler(client_id="id", client_secret="secret")
        with patch(
            "backend.services.crawlers.naver_news.requests.get",
            side_effect=_r.ConnectionError("network down"),
        ):
            result = crawler.fetch("삼성전자")
        assert result["items"] == []
        assert result["raw_text"] == ""

    def test_strip_html_helper(self):
        assert _strip_html("<b>hi</b>&amp;you") == "hi&you"
        assert _strip_html("") == ""


# ───────────── DartCrawler ─────────────


class TestDartCrawler:
    def test_corp_code_map_has_5_companies(self):
        for name in ("삼성전자", "SK하이닉스", "DB하이텍", "한미반도체", "솔브레인"):
            assert name in CORP_CODE_MAP
            assert CORP_CODE_MAP[name].isdigit()
            assert len(CORP_CODE_MAP[name]) == 8

    def test_not_configured_returns_empty(self):
        crawler = DartCrawler(api_key="")
        result = crawler.fetch("삼성전자")
        assert result["company_info"] == {}
        assert result["disclosures"] == []

    def test_unknown_company_returns_empty(self):
        crawler = DartCrawler(api_key="dummy")
        result = crawler.fetch("없는회사주식회사")
        assert result["company_info"] == {}

    def test_fetch_success(self):
        crawler = DartCrawler(api_key="dummy")
        company_resp = MagicMock()
        company_resp.json.return_value = {
            "status": "000",
            "corp_name": "삼성전자",
            "ceo_nm": "이재용",
            "est_dt": "19690113",
            "induty_code": "264",
            "adres": "수원시",
            "hm_url": "samsung.com",
            "stock_name": "삼성전자",
        }
        company_resp.raise_for_status = MagicMock()

        list_resp = MagicMock()
        list_resp.json.return_value = {
            "status": "000",
            "list": [
                {
                    "report_nm": "분기보고서",
                    "flr_nm": "삼성전자",
                    "rcept_dt": "20260515",
                    "rcept_no": "20260515000001",
                }
            ],
        }
        list_resp.raise_for_status = MagicMock()

        with patch(
            "backend.services.crawlers.dart.requests.get",
            side_effect=[company_resp, list_resp],
        ):
            result = crawler.fetch("삼성전자")

        assert result["company_info"]["corp_name"] == "삼성전자"
        assert len(result["disclosures"]) == 1
        assert "분기보고서" in result["raw_text"]


# ───────────── RecruitPageCrawler ─────────────


class TestRecruitPageCrawler:
    def test_empty_url_returns_empty(self):
        crawler = RecruitPageCrawler()
        result = crawler.fetch("삼성전자", "")
        assert result["raw_text"] == ""

    def test_extracts_talent_section(self):
        html = """
        <html>
          <body>
            <header>nav</header>
            <main>
              <section>
                <h2>인재상</h2>
                <p>도전 의식과 창의력으로 변화를 선도하는 인재를 추구합니다. 글로벌 마인드와 협업을 중시합니다.</p>
              </section>
              <footer>copyright</footer>
            </main>
          </body>
        </html>
        """
        fake_resp = MagicMock()
        fake_resp.text = html
        fake_resp.encoding = "utf-8"
        fake_resp.apparent_encoding = "utf-8"
        fake_resp.raise_for_status = MagicMock()

        crawler = RecruitPageCrawler()
        with patch(
            "backend.services.crawlers.recruit_page.requests.get", return_value=fake_resp
        ):
            result = crawler.fetch("삼성전자", "https://samsung-dsrecruit.com/")
        assert "인재상" in result["talent_text"] or "도전" in result["talent_text"]
        assert "도전" in result["raw_text"]

    def test_fetch_handles_network_error(self):
        import requests as _r

        crawler = RecruitPageCrawler()
        with patch(
            "backend.services.crawlers.recruit_page.requests.get",
            side_effect=_r.ConnectionError("DNS"),
        ):
            result = crawler.fetch("삼성전자", "https://invalid.example/")
        assert result["raw_text"] == ""


# ───────────── CompanySummarizer ─────────────


class TestCompanySummarizer:
    def test_fallback_when_no_client(self):
        s = CompanySummarizer(bedrock_client=None)
        long_text = "가" * 500
        out = s.summarize_talent("X", long_text)
        assert len(out) <= 110  # 100자 + 말줄임표

    def test_calls_llm_with_client(self):
        client = MagicMock()
        client.generate.return_value = "요약된 인재상 내용"
        s = CompanySummarizer(bedrock_client=client)
        out = s.summarize_talent("삼성전자", "원본 채용 페이지 텍스트", seed_text="기존 인재상")
        client.generate.assert_called_once()
        assert out == "요약된 인재상 내용"

    def test_llm_failure_falls_back(self):
        client = MagicMock()
        client.generate.side_effect = RuntimeError("Bedrock down")
        s = CompanySummarizer(bedrock_client=client)
        out = s.summarize_recent_trend("삼성전자", "뉴스 텍스트")
        # fallback이 동작하여 빈 문자열은 아니어야 함
        assert out
        assert "뉴스 텍스트" in out

    def test_empty_input_returns_seed(self):
        s = CompanySummarizer(bedrock_client=None)
        out = s.summarize_business_focus("X", dart_text="", seed_text="DRAM, HBM")
        assert out == "DRAM, HBM"


# ───────────── CrawlOrchestrator ─────────────


def _make_orchestrator(dry_run: bool = True, summarizer: CompanySummarizer | None = None):
    db = MagicMock()
    db.upsert_company_info.return_value = 42
    summ = summarizer or CompanySummarizer(bedrock_client=None)
    return db, CrawlOrchestrator(
        db=db,
        seeds=SAMPLE_SEEDS,
        naver=MagicMock(spec=NaverNewsCrawler),
        dart=MagicMock(spec=DartCrawler),
        recruit=MagicMock(spec=RecruitPageCrawler),
        summarizer=summ,
        sources=("naver", "dart", "recruit"),
        dry_run=dry_run,
    )


class TestCrawlOrchestrator:
    def test_unknown_company_returns_error(self):
        db, orch = _make_orchestrator(dry_run=True)
        result = orch.crawl_company("없는회사")
        assert result.success is False
        assert "unknown company" in (result.error or "")

    def test_all_sources_success_flow(self):
        db, orch = _make_orchestrator(dry_run=True)
        orch.naver.fetch.return_value = {
            "source": "naver_news",
            "company": "삼성전자",
            "items": [{"title": "t", "description": "d", "link": "", "pub_date": ""}],
            "raw_text": "1. t - d",
        }
        orch.dart.fetch.return_value = {
            "source": "dart",
            "company": "삼성전자",
            "corp_code": "00126380",
            "company_info": {"corp_name": "삼성전자"},
            "disclosures": [{"report_nm": "분기보고서"}],
            "raw_text": "기업명: 삼성전자",
        }
        orch.recruit.fetch.return_value = {
            "source": "recruit_page",
            "company": "삼성전자",
            "url": "https://www.samsung-dsrecruit.com/",
            "raw_text": "삼성전자 인재상 텍스트",
            "talent_text": "도전 인재 텍스트",
        }
        result = orch.crawl_company("삼성전자")
        assert result.success is True
        assert set(result.sources_ok) == {"naver", "dart", "recruit"}
        # dry-run이라 upsert 호출 안 됨
        db.upsert_company_info.assert_not_called()
        # info 페이로드 포함
        assert result.info["name"] == "삼성전자"

    def test_partial_failure_keeps_going(self):
        db, orch = _make_orchestrator(dry_run=True)
        orch.naver.fetch.side_effect = RuntimeError("naver down")
        orch.dart.fetch.return_value = {
            "source": "dart",
            "company": "삼성전자",
            "corp_code": "00126380",
            "company_info": {"corp_name": "삼성전자"},
            "disclosures": [],
            "raw_text": "기업개황",
        }
        orch.recruit.fetch.return_value = {
            "source": "recruit_page",
            "company": "삼성전자",
            "url": "",
            "raw_text": "",
            "talent_text": "",
        }
        result = orch.crawl_company("삼성전자")
        assert "naver" in result.sources_failed
        assert "dart" in result.sources_ok
        # 부분 성공도 success=True로 간주 (dart가 데이터 반환)
        assert result.success is True

    def test_db_upsert_called_when_not_dry_run(self):
        db, orch = _make_orchestrator(dry_run=False)
        orch.naver.fetch.return_value = {
            "source": "naver_news", "company": "삼성전자", "items": [{"title": "t"}], "raw_text": "x",
        }
        orch.dart.fetch.return_value = {
            "source": "dart", "company": "삼성전자", "corp_code": "00126380",
            "company_info": {}, "disclosures": [], "raw_text": "",
        }
        orch.recruit.fetch.return_value = {
            "source": "recruit_page", "company": "삼성전자", "url": "u",
            "raw_text": "", "talent_text": "",
        }
        result = orch.crawl_company("삼성전자")
        db.upsert_company_info.assert_called_once()
        assert result.db_id == 42

    def test_crawl_many_isolates_crashes(self):
        db, orch = _make_orchestrator(dry_run=True)
        orch.naver.fetch.return_value = {
            "source": "naver_news", "company": "x", "items": [], "raw_text": "",
        }
        orch.dart.fetch.return_value = {
            "source": "dart", "company": "x", "corp_code": None,
            "company_info": {}, "disclosures": [], "raw_text": "",
        }
        orch.recruit.fetch.return_value = {
            "source": "recruit_page", "company": "x", "url": "",
            "raw_text": "", "talent_text": "",
        }
        results = orch.crawl_many(["삼성전자", "없는회사", "SK하이닉스"])
        assert len(results) == 3
        names = [r.company for r in results]
        assert names == ["삼성전자", "없는회사", "SK하이닉스"]


# ───────────── 통합(라이브) 테스트 ─────────────


@pytest.mark.live
def test_live_naver_news_real_call():
    """실제 NAVER API 호출 (NAVER_CLIENT_ID/SECRET 필요). 기본 skip."""
    if not (os.getenv("NAVER_CLIENT_ID") and os.getenv("NAVER_CLIENT_SECRET")):
        pytest.skip("NAVER credentials not set")
    crawler = NaverNewsCrawler()
    result = crawler.fetch("삼성전자")
    assert result["items"]


@pytest.mark.live
def test_live_dart_real_call():
    """실제 DART API 호출 (DART_API_KEY 필요). 기본 skip."""
    if not os.getenv("DART_API_KEY"):
        pytest.skip("DART_API_KEY not set")
    crawler = DartCrawler()
    result = crawler.fetch("삼성전자")
    assert result["company_info"].get("corp_name")
