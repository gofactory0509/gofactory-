"""대화 관리 엔진 모듈.

면접 세션의 대화 이력을 관리한다.
Gemini API 형식에 맞게 메시지를 변환하여 제공한다.
"""


class ChatEngine:
    """면접 대화 관리 엔진.

    session_state를 사용하여 면접 대화 이력을 관리하며,
    Gemini API 형식으로 메시지를 변환한다.
    """

    MAX_MESSAGES: int = 30

    def __init__(self, session_state):
        """session_state를 사용하여 대화 이력 초기화.

        Args:
            session_state: Streamlit session_state 또는 dict-like 객체
        """
        self._session_state = session_state
        if "chat_history" not in self._session_state:
            self._session_state["chat_history"] = []

    def add_user_message(self, content: str) -> bool:
        """사용자 메시지를 대화 이력에 추가.

        Args:
            content: 사용자 입력 메시지

        Returns:
            bool: 메시지 추가 성공 여부
        """
        if not isinstance(content, str) or not content.strip():
            return False

        self._session_state["chat_history"].append(
            {"role": "user", "parts": [content]}
        )
        self._enforce_max_messages()
        return True

    def add_model_message(self, content: str) -> None:
        """AI 응답을 대화 이력에 추가.

        Args:
            content: AI가 생성한 응답 메시지
        """
        self._session_state["chat_history"].append(
            {"role": "model", "parts": [content]}
        )
        self._enforce_max_messages()

    def get_history(self) -> list[dict]:
        """현재 대화 이력 반환 (Gemini 형식).

        Returns:
            list[dict]: 대화 이력 리스트
        """
        return list(self._session_state["chat_history"])

    def reset(self) -> None:
        """대화 이력 초기화."""
        self._session_state["chat_history"] = []

    def _enforce_max_messages(self) -> None:
        """최대 메시지 수 제한 적용."""
        messages = self._session_state["chat_history"]
        if len(messages) > self.MAX_MESSAGES:
            self._session_state["chat_history"] = messages[-self.MAX_MESSAGES:]
