# -*- coding: utf-8 -*-
"""pytest 공통 설정.

- 커스텀 마커 등록 (live: 실제 외부 API 호출, 기본 deselect)
- 기본 실행 시 live 마커가 붙은 테스트는 자동 skip
"""

from __future__ import annotations

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: 실제 외부 API를 호출하는 통합 테스트 (기본 skip; 명시적으로 -m live 지정 시 실행)",
    )


def pytest_collection_modifyitems(config, items):
    """`-m live`가 명시되지 않으면 live 마커 붙은 테스트를 skip."""
    keyword = config.getoption("-m", default="") or ""
    if "live" in keyword:
        return
    skip_live = pytest.mark.skip(reason="live test (use -m live to run)")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
