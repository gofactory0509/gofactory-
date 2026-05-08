"""AI 클라이언트 모듈.

Google Gemini API를 사용하여 면접 질문 생성 및 답변 평가를 수행한다.
"""

import google.generativeai as genai


SYSTEM_PROMPT = (
    "너는 전문 면접관이야. 사용자가 선택한 직무에 맞는 면접 질문을 하고, "
    "답변에 대해 논리성, 핵심 키워드 포함 여부, 개선점을 구체적으로 피드백해줘. "
    "항상 한국어로 답변해."
)


class AIClient:
    """Google Gemini AI 클라이언트.

    Gemini 2.0 Flash 모델을 사용하여 면접 질문 생성 및 답변 평가를 수행한다.
    """

    MODEL_NAME: str = "gemini-2.0-flash-lite"

    def __init__(self, api_key: str):
        """Gemini 클라이언트 초기화.

        Args:
            api_key: Google Gemini API 인증 키

        Raises:
            ValueError: api_key가 빈 문자열이거나 None인 경우
        """
        if not self.validate_api_key(api_key):
            raise ValueError(
                "API 키가 유효하지 않습니다. 빈 문자열이거나 None일 수 없습니다."
            )

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            self.MODEL_NAME,
            system_instruction=SYSTEM_PROMPT,
        )

    def generate_response(self, messages: list[dict]) -> str:
        """대화 이력 기반 AI 응답 생성.

        Args:
            messages: Gemini 형식의 메시지 목록
                      [{"role": "user"|"model", "parts": [str]}, ...]

        Returns:
            str: AI 생성 응답 텍스트
        """
        chat = self.model.start_chat(history=messages[:-1] if len(messages) > 1 else [])
        last_message = messages[-1]["parts"][0] if messages else ""
        response = chat.send_message(last_message)
        return response.text

    def generate_question(self, job_field: str) -> str:
        """선택한 직무에 맞는 면접 질문 생성.

        Args:
            job_field: 직무 분야 (예: 반도체, 백엔드, 데이터, 마케팅)

        Returns:
            str: 생성된 면접 질문
        """
        prompt = (
            f"'{job_field}' 직무 면접에서 나올 수 있는 실전 면접 질문을 하나만 생성해줘. "
            f"질문만 간결하게 출력해. 번호나 부가 설명 없이 질문 하나만."
        )
        response = self.model.generate_content(prompt)
        return response.text.strip()

    def evaluate_answer(self, question: str, answer: str, job_field: str) -> str:
        """사용자 답변을 평가하고 피드백 제공.

        Args:
            question: 면접 질문
            answer: 사용자의 답변
            job_field: 직무 분야

        Returns:
            str: 평가 피드백 (논리성, 키워드, 개선점 포함)
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
        response = self.model.generate_content(prompt)
        return response.text.strip()

    def generate_daily_question(self) -> str:
        """오늘의 랜덤 면접 질문 생성.

        Returns:
            str: 랜덤 면접 질문
        """
        prompt = (
            "취업 면접에서 자주 나오는 공통 질문 중 하나를 랜덤으로 생성해줘. "
            "직무 무관하게 인성/역량 면접 질문이면 좋겠어. "
            "질문만 간결하게 출력해."
        )
        response = self.model.generate_content(prompt)
        return response.text.strip()

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """API 키 형식 유효성 검증.

        Args:
            api_key: 검증할 API 키 문자열

        Returns:
            bool: API 키가 유효하면 True
        """
        if api_key is None:
            return False
        if not isinstance(api_key, str):
            return False
        if not api_key.strip():
            return False
        return True
