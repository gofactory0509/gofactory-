# -*- coding: utf-8 -*-
"""DART OpenAPI 크롤러.

회사 기업개황(corpCode) 및 최근 공시 목록 수집.

환경변수:
    DART_API_KEY — opendart.fss.or.kr 발급
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests


logger = logging.getLogger(__name__)


# 회사별 corp_code 매핑 (DART OpenAPI 공개 corpCode)
# 검증 필요: 추후 corpCode.xml 일괄 다운로드로 자동 동기화 권장
CORP_CODE_MAP: dict[str, str] = {
    "삼성전자": "00126380",
    "SK하이닉스": "00164779",
    "DB하이텍": "00190321",      # 검증 필요 (구 동부하이텍 corp_code일 가능성)
    "한미반도체": "00164662",     # 검증 필요
    "솔브레인": "00126186",       # 검증 필요 (지주사/사업회사 분리 이슈 있음)
}


DART_COMPANY_ENDPOINT = "https://opendart.fss.or.kr/api/company.json"
DART_DISCLOSURE_ENDPOINT = "https://opendart.fss.or.kr/api/list.json"
DEFAULT_TIMEOUT = 10  # seconds


class DartCrawler:
    """DART OpenAPI 래퍼.

    - company.json: 기업개황(개요, 대표자, 설립일, 업종 등)
    - list.json: 최근 공시 목록
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        corp_code_map: dict[str, str] | None = None,
    ):
        self.api_key = api_key or os.getenv("DART_API_KEY", "")
        self.timeout = timeout
        self.corp_code_map = corp_code_map or CORP_CODE_MAP

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def get_corp_code(self, company_name: str) -> str | None:
        return self.corp_code_map.get(company_name)

    def fetch(self, company_name: str) -> dict[str, Any]:
        """회사 기본 정보 + 최근 공시 수집.

        Returns:
            dict: {"source": "dart", "company": str, "company_info": dict,
                   "disclosures": list, "raw_text": str}
        """
        if not self.is_configured():
            logger.warning("DartCrawler: DART_API_KEY not set, skipping")
            return self._empty(company_name)

        corp_code = self.get_corp_code(company_name)
        if not corp_code:
            logger.warning("DartCrawler: no corp_code for %s", company_name)
            return self._empty(company_name)

        company_info = self._fetch_company_info(corp_code)
        disclosures = self._fetch_recent_disclosures(corp_code)
        raw_text = self._build_raw_text(company_info, disclosures)

        return {
            "source": "dart",
            "company": company_name,
            "corp_code": corp_code,
            "company_info": company_info,
            "disclosures": disclosures,
            "raw_text": raw_text,
        }

    def _fetch_company_info(self, corp_code: str) -> dict[str, Any]:
        try:
            response = requests.get(
                DART_COMPANY_ENDPOINT,
                params={"crtfc_key": self.api_key, "corp_code": corp_code},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("DartCrawler.company_info failed (corp_code=%s): %s", corp_code, exc)
            return {}

        if data.get("status") != "000":
            logger.warning(
                "DartCrawler.company_info status=%s message=%s",
                data.get("status"),
                data.get("message"),
            )
            return {}
        return {
            "corp_name": data.get("corp_name", ""),
            "ceo_nm": data.get("ceo_nm", ""),
            "est_dt": data.get("est_dt", ""),
            "induty_code": data.get("induty_code", ""),
            "adres": data.get("adres", ""),
            "hm_url": data.get("hm_url", ""),
            "stock_name": data.get("stock_name", ""),
        }

    def _fetch_recent_disclosures(self, corp_code: str, page_count: int = 10) -> list[dict]:
        try:
            response = requests.get(
                DART_DISCLOSURE_ENDPOINT,
                params={
                    "crtfc_key": self.api_key,
                    "corp_code": corp_code,
                    "page_count": page_count,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("DartCrawler.disclosures failed (corp_code=%s): %s", corp_code, exc)
            return []

        if data.get("status") != "000":
            return []
        items = data.get("list", []) or []
        out = []
        for item in items:
            out.append(
                {
                    "report_nm": item.get("report_nm", ""),
                    "flr_nm": item.get("flr_nm", ""),
                    "rcept_dt": item.get("rcept_dt", ""),
                    "rcept_no": item.get("rcept_no", ""),
                }
            )
        return out

    @staticmethod
    def _empty(company_name: str) -> dict[str, Any]:
        return {
            "source": "dart",
            "company": company_name,
            "corp_code": None,
            "company_info": {},
            "disclosures": [],
            "raw_text": "",
        }

    @staticmethod
    def _build_raw_text(company_info: dict, disclosures: list[dict]) -> str:
        lines: list[str] = []
        if company_info:
            lines.append(
                f"기업명: {company_info.get('corp_name', '')} | 대표: {company_info.get('ceo_nm', '')} "
                f"| 설립일: {company_info.get('est_dt', '')} | 업종코드: {company_info.get('induty_code', '')}"
            )
            if company_info.get("adres"):
                lines.append(f"주소: {company_info['adres']}")
        if disclosures:
            lines.append("[최근 공시]")
            for idx, item in enumerate(disclosures, start=1):
                lines.append(
                    f"{idx}. {item.get('rcept_dt', '')} | {item.get('report_nm', '')} ({item.get('flr_nm', '')})"
                )
        return "\n".join(lines)
