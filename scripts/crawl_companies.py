# -*- coding: utf-8 -*-
"""회사 정보 크롤러 CLI 진입점.

사용 예:
    python scripts/crawl_companies.py --dry-run
    python scripts/crawl_companies.py --companies 삼성전자
    python scripts/crawl_companies.py --companies "삼성전자,SK하이닉스" --sources naver,dart

Exit code:
    0: 모든 회사 성공
    2: 부분 실패
    1: 전체 실패 또는 설정 오류
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path


# 프로젝트 루트를 sys.path에 추가 (스크립트 직접 실행 대응)
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from backend.services.crawlers.orchestrator import (  # noqa: E402
    CrawlOrchestrator,
    VALID_SOURCES,
)
from backend.services.crawlers.summarizer import CompanySummarizer  # noqa: E402
from database import COMPANY_SEEDS, InterviewDB  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Go터뷰 회사 정보 크롤러 PoC (네이버/DART/채용페이지 → LLM 요약 → DB upsert)"
    )
    parser.add_argument(
        "--companies",
        type=str,
        default="",
        help="쉼표 구분 회사명. 비우면 COMPANY_SEEDS 5개 전부.",
    )
    parser.add_argument(
        "--sources",
        type=str,
        default=",".join(VALID_SOURCES),
        help=f"쉼표 구분 소스. 기본={','.join(VALID_SOURCES)}",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="interviews.db",
        help="SQLite DB 경로 (기본: interviews.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="DB upsert를 건너뜀 (소스 호출/요약만 검증)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="DEBUG 로그 출력",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Bedrock 요약 호출 안 함 (raw fallback)",
    )
    return parser.parse_args(argv)


def build_summarizer(no_llm: bool) -> CompanySummarizer:
    """Bedrock 클라이언트 시도. credentials/모듈 미설치/예외 시 fallback."""
    if no_llm:
        logging.info("--no-llm 지정 → CompanySummarizer fallback 모드(raw truncate)")
        return CompanySummarizer(bedrock_client=None)

    # AWS 자격증명 빠른 체크 (없으면 LLM skip)
    has_creds = (
        os.getenv("AWS_ACCESS_KEY_ID")
        or os.getenv("AWS_PROFILE")
        or os.getenv("AWS_ROLE_ARN")
        or os.path.exists(os.path.expanduser("~/.aws/credentials"))
    )
    if not has_creds:
        logging.warning("AWS 자격증명 미발견 → CompanySummarizer fallback 모드(raw truncate)")
        return CompanySummarizer(bedrock_client=None)

    try:
        from backend.services.bedrock_client import BedrockClient

        client = BedrockClient()
        return CompanySummarizer(bedrock_client=client)
    except Exception as exc:
        logging.warning("BedrockClient 초기화 실패 → fallback 모드: %s", exc)
        return CompanySummarizer(bedrock_client=None)


def resolve_companies(arg: str) -> list[str]:
    if not arg.strip():
        return [seed["name"] for seed in COMPANY_SEEDS]
    return [c.strip() for c in arg.split(",") if c.strip()]


def resolve_sources(arg: str) -> list[str]:
    requested = [s.strip().lower() for s in arg.split(",") if s.strip()]
    out = [s for s in requested if s in VALID_SOURCES]
    invalid = [s for s in requested if s not in VALID_SOURCES]
    if invalid:
        logging.warning("무시된 invalid sources: %s", invalid)
    if not out:
        logging.warning("유효 소스 없음 → 기본값 사용 %s", VALID_SOURCES)
        return list(VALID_SOURCES)
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("crawl_companies")

    companies = resolve_companies(args.companies)
    sources = resolve_sources(args.sources)
    logger.info(
        "대상 회사=%s | 소스=%s | db=%s | dry_run=%s",
        companies, sources, args.db_path, args.dry_run,
    )

    db = InterviewDB(db_path=args.db_path)
    summarizer = build_summarizer(no_llm=args.no_llm)

    orchestrator = CrawlOrchestrator(
        db=db,
        seeds=COMPANY_SEEDS,
        summarizer=summarizer,
        sources=sources,
        dry_run=args.dry_run,
    )

    results = orchestrator.crawl_many(companies)

    # 요약 출력
    total = len(results)
    succ = sum(1 for r in results if r.success)
    fail = total - succ
    logger.info("=" * 60)
    for r in results:
        logger.info(r.short())
        if r.error:
            logger.info("  error: %s", r.error)
        if r.db_id:
            logger.info("  db_id=%s", r.db_id)
    logger.info("=" * 60)
    logger.info("완료: total=%d, success=%d, fail=%d", total, succ, fail)

    db.close()

    if succ == total:
        return 0
    if succ == 0:
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
