# -*- coding: utf-8 -*-
"""AI 서비스 모듈.

Google Gemini API를 기본으로 사용하고, 실패 시 Groq API로 자동 폴백한다.
기존 ai_client.py의 로직을 FastAPI 서비스 구조로 리팩토링.
"""

import re

import google.generativeai as genai
from openai import OpenAI

from backend.config import settings

SYSTEM_PROMPT = (
    "너는 전문 면접관이야. 사용자가 선택한 직무에 맞는 면접 질문을 하고, "
    "답변에 대해 논리성, 핵심 키워드 포함 여부, 개선점을 구체적으로 피드백해줘. "
    "반드시 한국어로만 답변해. 한자(漢字), 중국어, 일본어, 키릴 문자 등 외국 문자를 절대 사용하지 마. "
    "한글, 영문 알파벳, 숫자, 기본 문장부호만 사용해."
)


class AIService:
    """AI 서비스 (Gemini 우선, Groq 폴백).

    settings에서 API 키를 읽어 Gemini와 Groq 클라이언트를 초기화한다.
    generate_question()과 evaluate_answer()를 통해 면접 질문 생성 및 답변 평가를 수행한다.
    """

    def __init__(self):
        self._gemini_model = None
        self._groq_client = None

        # Gemini 설정
        if settings.gemini_api_key and settings.gemini_api_key.strip():
            try:
                genai.configure(api_key=settings.gemini_api_key)
                self._gemini_model = genai.GenerativeModel(
                    "gemini-2.0-flash",
                    system_instruction=SYSTEM_PROMPT,
                )
            except Exception:
                self._gemini_model = None

        # Groq 폴백 설정
        if settings.groq_api_key and settings.groq_api_key.strip():
            self._groq_client = OpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )

    def _call_gemini(self, prompt: str) -> str:
        """Gemini API로 응답 생성."""
        response = self._gemini_model.generate_content(prompt)
        return response.text.strip()

    def _call_groq(self, prompt: str) -> str:
        """Groq API로 응답 생성."""
        response = self._groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content

    def _call(self, prompt: str) -> str:
        """Gemini 시도 → 실패 시 Groq 폴백.

        두 모델 모두 실패하면 RuntimeError를 발생시킨다.
        """
        if self._gemini_model:
            try:
                return self._call_gemini(prompt)
            except Exception:
                pass

        if self._groq_client:
            try:
                return self._call_groq(prompt)
            except Exception:
                pass

        raise RuntimeError("사용 가능한 AI 모델이 없습니다. API 키를 확인해주세요.")

    def generate_question(self, job_field: str, past_questions: list[str] | None = None) -> str:
        """직무별 면접 질문을 생성한다.

        Args:
            job_field: 직무 분야 (예: 반도체, 백엔드, 데이터, 마케팅 등)
            past_questions: 이전에 출제된 질문 목록 (중복 방지용)

        Returns:
            AI가 생성한 면접 질문 문자열
        """
        prompt = (
            f"'{job_field}' 직무 면접에서 나올 수 있는 실전 면접 질문을 하나만 생성해줘. "
            f"질문만 간결하게 출력해. 번호나 부가 설명 없이 질문 하나만."
        )
        if past_questions:
            past_list = "\n".join(f"- {q}" for q in past_questions[:5])
            prompt += f"\n\n이전에 출제된 질문들 (중복 피해주세요):\n{past_list}"
        return self._call(prompt)

    def evaluate_answer(self, question: str, answer: str, job_field: str) -> str:
        """면접 답변을 평가한다.

        Args:
            question: 면접 질문
            answer: 지원자 답변
            job_field: 직무 분야

        Returns:
            AI가 생성한 피드백 문자열 (논리성, 키워드, 개선점, 총평 포함)
        """
        prompt = (
            f"직무: {job_field}\n"
            f"면접 질문: {question}\n"
            f"지원자 답변: {answer}\n\n"
            f"위 답변을 다음 기준으로 평가해줘:\n"
            f"1. **논리성** (1~10점): 답변의 논리적 구조와 일관성\n"
            f"2. **핵심 키워드**: 답변에 포함된/빠진 중요 키워드 분석\n"
            f"3. **개선점**: 구체적인 개선 방향과 모범 답변 예시\n"
            f"4. **총평**: 전체적인 한줄 평가\n\n"
            f"친절하지만 전문적인 톤으로 피드백해줘."
        )
        return self._call(prompt)

    @staticmethod
    def extract_score(feedback: str) -> int | None:
        """피드백 텍스트에서 논리성 점수를 추출한다.

        Args:
            feedback: AI가 생성한 피드백 텍스트

        Returns:
            1~10 범위의 점수, 추출 실패 시 None
        """
        match = re.search(r"(\d{1,2})\s*[점/]?\s*(?:점|/10)", feedback)
        if match:
            score = int(match.group(1))
            return min(max(score, 1), 10)
        return None

    @staticmethod
    def extract_section(feedback: str, section_name: str) -> str:
        """피드백 텍스트에서 특정 섹션의 내용을 추출한다.

        Args:
            feedback: AI가 생성한 피드백 텍스트
            section_name: 추출할 섹션 이름 (예: "논리성", "핵심 키워드", "개선점", "총평")

        Returns:
            해당 섹션의 내용 문자열, 찾지 못하면 빈 문자열
        """
        pattern = rf"\*?\*?{re.escape(section_name)}\*?\*?[:\s]*(.*?)(?=\n\*?\*?\d|\n\*?\*?[가-힣]|\Z)"
        match = re.search(pattern, feedback, re.DOTALL)
        return match.group(1).strip() if match else ""
