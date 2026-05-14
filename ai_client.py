# -*- coding: utf-8 -*-
"""AI 클라이언트 모듈.

Google Gemini API를 기본으로 사용하고, 실패 시 Groq API로 자동 전환한다.
"""

import google.generativeai as genai
from openai import OpenAI


SYSTEM_PROMPT = (
    "너는 전문 면접관이야. 사용자가 선택한 직무에 맞는 면접 질문을 하고, "
    "답변에 대해 논리성, 핵심 키워드 포함 여부, 개선점을 구체적으로 피드백해줘. "
    "반드시 한국어로만 답변해. 한자(漢字), 중국어, 일본어, 키릴 문자 등 외국 문자를 절대 사용하지 마. "
    "한글, 영문 알파벳, 숫자, 기본 문장부호만 사용해."
)


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

    def generate_question(self, job_field: str, context_hint: str = "", interview_type: str = "직무면접", resume_content: str = "") -> str:
        if interview_type == "자소서기반면접" and resume_content:
            prompt = (
                f"아래는 '{job_field}' 직무에 지원한 지원자의 자기소개서야:\n\n"
                f"---\n{resume_content}\n---\n\n"
                f"이 자기소개서 내용을 바탕으로 면접관이 물어볼 수 있는 "
                f"날카롭고 구체적인 면접 질문을 하나만 생성해줘. "
                f"자소서에 적힌 경험, 역량, 지원동기 등을 파고드는 질문이어야 해. "
                f"질문만 간결하게 출력해."
            )
        elif interview_type == "인성면접":
            prompt = (
                f"'{job_field}' 직무 면접에서 나올 수 있는 인성 면접 질문을 하나만 생성해줘. "
                f"지원자의 가치관, 팀워크, 갈등 해결, 리더십, 스트레스 관리, 실패 경험 등 "
                f"인성/역량을 평가하는 질문이어야 해. "
                f"질문만 간결하게 출력해."
            )
        else:
            prompt = (
                f"'{job_field}' 직무 면접에서 나올 수 있는 실전 면접 질문을 하나만 생성해줘. "
                f"직무 전문 지식이나 기술적 역량을 평가하는 질문이어야 해. "
                f"질문만 간결하게 출력해. 번호나 부가 설명 없이 질문 하나만."
            )
        if context_hint:
            prompt += context_hint
        return self._call(prompt)

    def evaluate_answer(self, question: str, answer: str, job_field: str, interview_type: str = "직무면접") -> str:
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

        prompt = (
            f"직무: {job_field}\n"
            f"면접 유형: {interview_type}\n"
            f"면접 질문: {question}\n"
            f"지원자 답변: {answer}\n\n"
            f"{type_guidance}"
            f"위 답변을 다음 기준으로 평가해줘:\n"
            f"1. **논리성** (1~10점): 답변의 논리적 구조와 일관성\n"
            f"2. **핵심 키워드**: 답변에 포함된/빠진 중요 키워드 분석\n"
            f"3. **개선점**: 구체적인 개선 방향과 모범 답변 예시\n"
            f"4. **총평**: 전체적인 한줄 평가\n\n"
            f"반드시 첫 줄에 '논리성 점수: X/10' 형식으로 점수를 명시해줘.\n"
            f"친절하지만 전문적인 톤으로 피드백해줘."
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
