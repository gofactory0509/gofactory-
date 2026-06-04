# -*- coding: utf-8 -*-
"""면접 도메인 LLM 호출 어댑터.

v4부터는 BYOK(사용자 OpenRouter 키) 경로를 제거하고 AWS Bedrock 단일 백엔드로
통일했다. 사용자 측 LLM 활용은 ``backend/mcp_server.py`` 의 MCP 서버로 일원화
(Claude Pro 정액 구독에서 직접 호출).

이름은 호환을 위해 ``LLMRouter`` 로 유지하지만 실제로는 BedrockClient를 감싸는
얇은 도메인 서비스다.
"""

from __future__ import annotations

from backend.services.bedrock_client import BedrockClient


class LLMRouter:
    """면접 질문 생성·답변 평가를 Bedrock으로 위임하는 서비스.

    이전 v3에서는 BYOK 키 유무에 따라 OpenRouter / Bedrock 라우팅을 했으나,
    v4부터는 항상 Bedrock 단일 백엔드. 사용자 측 LLM은 MCP 서버 경로로만 노출.
    """

    def __init__(self):
        # 후방 호환: 기존 코드가 인자를 넘겨도 무시한다.
        pass

    def _client(self) -> BedrockClient:
        return BedrockClient()

    def backend_name(self) -> str:
        return "bedrock"

    # ─── 면접 도메인 메서드 ───

    def generate_question(
        self,
        job_field: str,
        context_hint: str = "",
        interview_type: str = "직무면접",
        resume_content: str = "",
        company: str = "",
        business_unit: str = "",
        company_info: dict | None = None,
    ) -> str:
        company_context = ""
        if company:
            company_context = (
                f"지원 회사는 '{company}'이야. 이 회사의 인재상, 직무 특성, "
                f"최신 동향을 반영한 질문을 만들어줘. "
            )
        if company_info:
            company_context += (
                f"\n[참고 - {company_info.get('name', company)} 정보]\n"
                f"- 인재상: {company_info.get('talent_profile', '')}\n"
                f"- 주력 사업: {company_info.get('business_focus', '')}\n"
                f"- 최근 트렌드: {company_info.get('recent_news_summary', '')}\n"
                f"위 정보를 반드시 질문에 녹여서, 이 회사 면접에서 실제로 나올 법한 "
                f"구체적 질문을 만들어줘.\n"
            )

        job_context = f"'{job_field}'"
        if business_unit:
            job_context += f" 직무 (사업부: {business_unit})"
            company_context += (
                f"사업부 '{business_unit}'의 특성(주력 제품, 핵심 기술, 최근 동향)을 "
                f"반영한 질문을 만들어줘. "
            )
        else:
            job_context += " 직무"

        if interview_type == "자소서기반면접" and resume_content:
            prompt = (
                f"아래는 {job_context}에 지원한 지원자의 자기소개서야:\n\n"
                f"---\n{resume_content}\n---\n\n"
                f"{company_context}"
                f"이 자기소개서 내용을 바탕으로 면접관이 물어볼 수 있는 "
                f"날카롭고 구체적인 면접 질문을 하나만 생성해줘. "
                f"자소서에 적힌 경험, 역량, 지원동기 등을 파고드는 질문이어야 해. "
                f"질문만 간결하게 출력해."
            )
        elif interview_type == "인성면접":
            prompt = (
                f"{job_context} 면접에서 나올 수 있는 인성 면접 질문을 하나만 생성해줘. "
                f"{company_context}"
                f"지원자의 가치관, 팀워크, 갈등 해결, 리더십, 스트레스 관리, "
                f"실패 경험 등 인성/역량을 평가하는 질문이어야 해. "
                f"질문만 간결하게 출력해."
            )
        else:
            prompt = (
                f"{job_context} 면접에서 나올 수 있는 실전 면접 질문을 하나만 생성해줘. "
                f"{company_context}"
                f"직무 전문 지식이나 기술적 역량을 평가하는 질문이어야 해. "
                f"해당 직무의 최신 트렌드와 현장 실무를 반영한 질문이면 좋겠어. "
                f"질문만 간결하게 출력해. 번호나 부가 설명 없이 질문 하나만."
            )
        if context_hint:
            prompt += context_hint
        return self._client().generate(prompt)

    def evaluate_answer(
        self,
        question: str,
        answer: str,
        job_field: str,
        interview_type: str = "직무면접",
        company: str = "",
        business_unit: str = "",
        company_info: dict | None = None,
    ) -> str:
        type_guidance = ""
        if interview_type == "인성면접":
            type_guidance = (
                "이 질문은 인성면접 질문이야. "
                "답변의 진정성, 구체적 경험 활용, 자기인식, 성장 가능성을 "
                "중심으로 평가해줘.\n"
            )
        elif interview_type == "자소서기반면접":
            type_guidance = (
                "이 질문은 자소서 기반 면접 질문이야. "
                "자소서 내용과의 일관성, 구체적 사례 제시, 깊이 있는 답변인지를 "
                "중심으로 평가해줘.\n"
            )

        company_context = ""
        if company:
            company_context = (
                f"지원 회사: {company}\n"
                f"이 회사의 인재상과 직무 특성을 고려하여 평가해줘.\n"
            )

        bu_context = ""
        if business_unit:
            bu_context = (
                f"사업부: {business_unit}\n"
                f"해당 사업부의 주력 제품·핵심 기술과 답변의 적합성을 함께 평가해줘.\n"
            )

        if company_info:
            company_context += (
                f"\n[참고 - {company_info.get('name', company)} 정보]\n"
                f"- 인재상: {company_info.get('talent_profile', '')}\n"
                f"- 주력 사업: {company_info.get('business_focus', '')}\n"
                f"- 최근 트렌드: {company_info.get('recent_news_summary', '')}\n"
                f"이 회사의 인재상과 주력 사업에 대한 답변의 적합성을 "
                f"반드시 평가에 반영하고, 피드백에 회사 특성을 언급해줘.\n"
            )

        prompt = (
            f"직무: {job_field}\n"
            f"{bu_context}"
            f"면접 유형: {interview_type}\n"
            f"{company_context}"
            f"면접 질문: {question}\n"
            f"지원자 답변: {answer}\n\n"
            f"{type_guidance}"
            f"위 답변을 아래 5개 항목으로 평가해줘. 각 항목은 20점 만점이야:\n\n"
            f"1. **논리성** (X/20): 두괄식 구성인지, 결론→근거→예시 순서로 답변했는지 평가. "
            f"미괄식이거나 결론이 뒤에 나오면 감점.\n"
            f"2. **직무 적합성** (X/20): 해당 직무에서 요구하는 핵심 역량과 키워드가 포함되었는지, "
            f"현장 실무와 최신 트렌드를 반영했는지 평가.\n"
            f"3. **구체성** (X/20): 추상적 답변이 아닌 구체적 수치·사례·경험이 포함되었는지.\n"
            f"4. **표현력** (X/20): 간결하고 명확한 표현인지.\n"
            f"5. **차별성** (X/20): 다른 지원자와 차별화되는 강점이 드러나는지.\n\n"
            f"반드시 아래 형식으로 점수를 출력해줘:\n"
            f"[점수] 논리성: X/20 | 직무적합성: X/20 | 구체성: X/20 | 표현력: X/20 | "
            f"차별성: X/20 | 총점: XX/100\n\n"
            f"각 항목별로 구체적 개선점과 모범 답변 예시를 제시하고, "
            f"마지막에 총평 한 줄을 작성해줘."
        )
        return self._client().generate(prompt)
