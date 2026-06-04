# -*- coding: utf-8 -*-
"""평가 루브릭 빌더.

MCP 서버와 (Phase 2 이후) FastAPI ``/api/evaluate`` 둘 다에서 사용한다.

Phase 1(현재)은 5축 표준 루브릭 + 직무/회사 컨텍스트 주입만 제공한다.
Phase 2에서 직무별 핵심 키워드, 회사별 인재상 가중치, Few-shot 채점 예시를
추가해 "그렇습니다" 같은 회피성 답변이 72점을 받지 못하도록 강화한다.
"""
from __future__ import annotations

# 5축 평가 기준 (각 20점, 합 100점)
EVALUATION_AXES = {
    "논리성": "두괄식 구성·결론→근거→예시 흐름. 미괄식·논점 흐림은 감점.",
    "직무적합성": "직무 핵심 키워드·역량·현장 실무·최신 트렌드 반영도.",
    "구체성": "수치·사례·경험의 구체성. 추상적 진술은 감점.",
    "표현력": "간결성·명확성·전문 용어 정확도.",
    "차별성": "다른 지원자와 구별되는 본인만의 관점·강점.",
}


def build_rubric(job_field: str, interview_type: str = "직무면접") -> dict:
    """주어진 직무·면접유형에 대한 평가 루브릭을 반환한다.

    Phase 1: 5축 표준 + 면접유형 가이드 + 직무명 echo.
    Phase 2: 직무별 핵심 키워드, 회피성 답변 감점 규칙, Few-shot 예시 추가 예정.

    Args:
        job_field: 직무 이름 (예: "회로설계", "메모리설계").
        interview_type: "직무면접" | "인성면접" | "자소서기반면접".

    Returns:
        Claude/Bedrock 시스템 프롬프트에 주입 가능한 dict.
    """
    type_focus = {
        "직무면접": "직무 전문 지식·역량·현장 실무를 중심으로 평가.",
        "인성면접": "지원자의 가치관·팀워크·갈등 해결·성장 가능성을 중심으로 평가.",
        "자소서기반면접": "자소서 내용과의 일관성·깊이·구체적 사례 활용을 중심으로 평가.",
    }.get(interview_type, "직무 전문성 위주로 평가.")

    return {
        "job_field": job_field,
        "interview_type": interview_type,
        "axes": EVALUATION_AXES,
        "scoring_scale": "각 축 0~20점, 총점 100점 만점",
        "type_focus": type_focus,
        "minimum_answer_length": 50,  # Phase 2에서 결정론적 가드로 사용
        "auto_low_score_patterns": [
            "그렇습니다", "네", "아니오", "잘 모르겠습니다", "노력하겠습니다",
        ],  # 회피성/공허 답변. Phase 2에서 정규식 가드로 강제 30점 이하.
        "output_format": (
            "[점수] 논리성: X/20 | 직무적합성: X/20 | 구체성: X/20 | "
            "표현력: X/20 | 차별성: X/20 | 총점: XX/100\n"
            "이어서 각 축별 구체 근거(왜 그 점수인지) + 개선점 + 모범 답변 예시 + 총평 1줄."
        ),
    }
