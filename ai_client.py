# -*- coding: utf-8 -*-
"""AI 클라이언트 모듈.

Google Gemini API를 기본으로 사용하고, 실패 시 Groq API로 자동 전환한다.
"""

import re

import google.generativeai as genai
from openai import OpenAI


SYSTEM_PROMPT = (
    "너는 전문 면접관이야. 사용자가 선택한 직무에 맞는 면접 질문을 하고, "
    "답변에 대해 논리성, 핵심 키워드 포함 여부, 개선점을 구체적으로 피드백해줘. "
    "반드시 한국어로만 답변해. 한자(漢字), 중국어, 일본어, 키릴 문자 등 외국 문자를 절대 사용하지 마. "
    "한글, 영문 알파벳, 숫자, 기본 문장부호만 사용해."
)


def parse_detail_scores(feedback_text: str) -> dict:
    """피드백 텍스트에서 항목별 점수(0~20)를 추출.

    Returns:
        {'논리성': int|None, '직무적합성': int|None, '구체성': int|None,
         '표현력': int|None, '차별성': int|None}
        각 키는 항상 존재하며, 추출 실패 시 값은 None.
    """
    patterns = {
        "논리성": r'논리성\s*[:：]\s*(\d+)\s*/\s*20',
        "직무적합성": r'직무\s*적합성\s*[:：]\s*(\d+)\s*/\s*20',
        "구체성": r'구체성\s*[:：]\s*(\d+)\s*/\s*20',
        "표현력": r'표현력\s*[:：]\s*(\d+)\s*/\s*20',
        "차별성": r'차별성\s*[:：]\s*(\d+)\s*/\s*20',
    }
    scores: dict = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, feedback_text or "")
        if match:
            try:
                value = int(match.group(1))
                scores[key] = value if 0 <= value <= 20 else None
            except (ValueError, TypeError):
                scores[key] = None
        else:
            scores[key] = None
    return scores


class AIClient:
    """AI 클라이언트 (Gemini 우선, Groq 백업)."""

    def __init__(self, gemini_key: str = None, groq_key: str = None):
        self.gemini_key = gemini_key
        self.groq_key = groq_key
        self.using_groq = False

        # Gemini 설정
        if gemini_key and gemini_key.strip():
            try:
                genai.configure(api_key=gemini_key)
                self.gemini_model = genai.GenerativeModel(
                    "gemini-2.0-flash",
                    system_instruction=SYSTEM_PROMPT,
                )
            except Exception:
                self.gemini_model = None
        else:
            self.gemini_model = None

        # Groq 백업 설정
        if groq_key and groq_key.strip():
            self.groq_client = OpenAI(
                api_key=groq_key,
                base_url="https://api.groq.com/openai/v1",
            )
        else:
            self.groq_client = None

    def _call_groq(self, prompt: str) -> str:
        """Groq API로 응답 생성."""
        response = self.groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content

    def _call_gemini(self, prompt: str) -> str:
        """Gemini API로 응답 생성."""
        response = self.gemini_model.generate_content(prompt)
        return response.text.strip()

    def _call(self, prompt: str) -> str:
        """Gemini 시도 → 실패 시 Groq으로 자동 전환."""
        # Gemini 먼저 시도
        if self.gemini_model and not self.using_groq:
            try:
                return self._call_gemini(prompt)
            except Exception:
                self.using_groq = True

        # Groq 백업
        if self.groq_client:
            return self._call_groq(prompt)

        raise RuntimeError("사용 가능한 AI 모델이 없습니다. API 키를 확인해주세요.")

    def generate_question(self, job_field: str, context_hint: str = "", interview_type: str = "직무면접", resume_content: str = "", company: str = "", business_unit: str = "", company_info: dict | None = None) -> str:
        company_context = ""
        if company:
            company_context = f"지원 회사는 '{company}'이야. 이 회사의 인재상, 직무 특성, 최신 동향을 반영한 질문을 만들어줘. "

        # 캐시된 회사 정보가 있으면 프롬프트에 구체 정보 주입
        if company_info:
            company_context += (
                f"\n[참고 - {company_info.get('name', company)} 정보]\n"
                f"- 인재상: {company_info.get('talent_profile', '')}\n"
                f"- 주력 사업: {company_info.get('business_focus', '')}\n"
                f"- 최근 트렌드: {company_info.get('recent_news_summary', '')}\n"
                f"위 정보를 반드시 질문에 녹여서, 이 회사 면접에서 실제로 나올 법한 구체적 질문을 만들어줘.\n"
            )

        job_context = f"'{job_field}'"
        if business_unit:
            job_context += f" 직무 (사업부: {business_unit})"
            company_context += f"사업부 '{business_unit}'의 특성(주력 제품, 핵심 기술, 최근 동향)을 반영한 질문을 만들어줘. "
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
                f"지원자의 가치관, 팀워크, 갈등 해결, 리더십, 스트레스 관리, 실패 경험 등 "
                f"인성/역량을 평가하는 질문이어야 해. "
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
        return self._call(prompt)

    def evaluate_answer(self, question: str, answer: str, job_field: str, interview_type: str = "직무면접", company: str = "", business_unit: str = "", company_info: dict | None = None) -> str:
        type_guidance = ""
        if interview_type == "인성면접":
            type_guidance = (
                "이 질문은 인성면접 질문이야. "
                "답변의 진정성, 구체적 경험 활용, 자기인식, 성장 가능성을 중심으로 평가해줘.\n"
            )
        elif interview_type == "자소서기반면접":
            type_guidance = (
                "이 질문은 자소서 기반 면접 질문이야. "
                "자소서 내용과의 일관성, 구체적 사례 제시, 깊이 있는 답변인지를 중심으로 평가해줘.\n"
            )

        company_context = ""
        if company:
            company_context = f"지원 회사: {company}\n이 회사의 인재상과 직무 특성을 고려하여 평가해줘.\n"

        # 캐시된 회사 정보가 있으면 평가 기준에 구체 정보 주입
        if company_info:
            company_context += (
                f"\n[참고 - {company_info.get('name', company)} 정보]\n"
                f"- 인재상: {company_info.get('talent_profile', '')}\n"
                f"- 주력 사업: {company_info.get('business_focus', '')}\n"
                f"- 최근 트렌드: {company_info.get('recent_news_summary', '')}\n"
                f"이 회사의 인재상과 주력 사업에 대한 답변의 적합성을 반드시 평가에 반영하고, "
                f"피드백에 회사 특성을 언급해줘.\n"
            )

        bu_context = ""
        if business_unit:
            bu_context = f"사업부: {business_unit}\n해당 사업부의 주력 제품·핵심 기술과 답변의 적합성을 함께 평가해줘.\n"

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
            f"미괄식이거나 결론이 뒤에 나오면 감점. 답변의 논리적 흐름과 구조를 평가해.\n"
            f"2. **직무 적합성** (X/20): 해당 직무에서 요구하는 핵심 역량과 키워드가 포함되었는지, "
            f"현장 실무와 최신 트렌드를 반영했는지 평가. 틀린 정보나 구시대적 내용이 있으면 반드시 지적해.\n"
            f"3. **구체성** (X/20): 추상적 답변이 아닌 구체적 수치, 사례, 경험이 포함되었는지 평가. "
            f"'열심히 했다' 같은 모호한 표현은 감점.\n"
            f"4. **표현력** (X/20): 간결하고 명확한 표현인지, 불필요한 반복이나 장황한 설명은 없는지 평가. "
            f"면접관이 듣기 편한 답변인지 평가해.\n"
            f"5. **차별성** (X/20): 다른 지원자와 차별화되는 나만의 강점이나 관점이 드러나는지 평가.\n\n"
            f"반드시 아래 형식으로 점수를 출력해줘:\n"
            f"[점수] 논리성: X/20 | 직무적합성: X/20 | 구체성: X/20 | 표현력: X/20 | 차별성: X/20 | 총점: XX/100\n\n"
            f"각 항목별로 구체적인 개선점과 모범 답변 예시를 제시해줘. "
            f"특히 두괄식 구성이 안 되어 있으면 두괄식으로 재구성한 예시를 보여줘. "
            f"직무 관련 최신 트렌드나 팩트가 틀렸으면 정확한 정보를 알려줘. "
            f"항목마다 다른 개선 포인트를 제시해야 해 (같은 피드백 반복 금지). "
            f"마지막에 총평 한줄을 작성해줘."
        )
        return self._call(prompt)

    def generate_daily_question(self) -> str:
        prompt = (
            "취업 면접에서 자주 나오는 공통 질문 중 하나를 랜덤으로 생성해줘. "
            "직무 무관하게 인성/역량 면접 질문이면 좋겠어. "
            "질문만 간결하게 출력해."
        )
        return self._call(prompt)

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        if api_key is None:
            return False
        if not isinstance(api_key, str):
            return False
        if not api_key.strip():
            return False
        return True

    def transcribe_audio(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        """Transcribe Korean speech to text via Gemini multimodal.

        Raises RuntimeError if Gemini is unavailable (no Groq audio fallback)."""
        if self.gemini_model is None:
            raise RuntimeError("음성 전사를 위해 Gemini API 키가 필요합니다.")
        try:
            content = [
                {"mime_type": mime_type, "data": audio_bytes},
                "이 한국어 음성을 정확히 받아써줘. 음성 내용만 출력하고 설명이나 따옴표는 붙이지 마. 한자, 일본어 등 외국 문자는 사용하지 마.",
            ]
            response = self.gemini_model.generate_content(content)
            return response.text.strip()
        except Exception as e:
            raise RuntimeError(f"음성 전사 실패: {e}")

    def generate_targeted_question(
        self,
        job_field: str,
        weakness: str,
        interview_type: str = "직무면접",
        business_unit: str = "",
        resume_content: str = "",
    ) -> str:
        """약점 영역을 집중 평가하는 맞춤 면접 질문 생성.

        generate_question의 프롬프트 스캐폴딩을 재사용하면서, 응시자의 특정 약점
        역량을 집중적으로 검증하도록 디렉티브를 덧붙인다.

        Args:
            job_field: 직무 분야
            weakness: 보강할 약점 영역 (논리성/직무적합성/구체성/표현력/차별성)
            interview_type: 면접 유형
            business_unit: 사업부 (선택)
            resume_content: 자소서 내용 (자소서기반면접 시)

        Returns:
            str: 생성된 면접 질문
        """
        job_context = f"'{job_field}'"
        if business_unit:
            job_context += f" 직무 (사업부: {business_unit})"
        else:
            job_context += " 직무"

        bu_context = ""
        if business_unit:
            bu_context = (
                f"사업부 '{business_unit}'의 특성(주력 제품, 핵심 기술, 최근 동향)을 반영한 질문을 만들어줘. "
            )

        if interview_type == "자소서기반면접" and resume_content:
            base = (
                f"아래는 {job_context}에 지원한 지원자의 자기소개서야:\n\n"
                f"---\n{resume_content}\n---\n\n"
                f"{bu_context}"
                f"이 자기소개서 내용을 바탕으로 면접관이 물어볼 수 있는 "
                f"날카롭고 구체적인 면접 질문을 하나만 생성해줘."
            )
        elif interview_type == "인성면접":
            base = (
                f"{job_context} 면접에서 나올 수 있는 인성 면접 질문을 하나만 생성해줘. "
                f"{bu_context}"
                f"지원자의 가치관, 팀워크, 갈등 해결, 리더십 등 인성/역량을 평가하는 질문이어야 해."
            )
        else:
            base = (
                f"{job_context} 면접에서 나올 수 있는 실전 면접 질문을 하나만 생성해줘. "
                f"{bu_context}"
                f"직무 전문 지식이나 기술적 역량을 평가하는 질문이어야 해. "
                f"해당 직무의 최신 트렌드와 현장 실무를 반영한 질문이면 좋겠어."
            )

        directive = (
            f" 이 질문은 응시자의 '{weakness}' 역량을 집중적으로 평가하도록 설계해. "
            f"답변자가 그 역량을 보여주지 않으면 좋은 점수를 받기 어려운 질문을 만들어줘. "
            f"질문만 출력하고 다른 설명은 붙이지 마."
        )
        prompt = base + directive
        return self._call(prompt)
