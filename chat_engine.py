"""대화 관리 엔진 모듈.

ChatEngine은 Streamlit session_state를 사용하여 대화 이력을 관리한다.
사용자 메시지와 AI 응답을 저장하고, 최대 50개 메시지 제한을 적용한다.
"""


class ChatEngine:
    """대화 관리 엔진.

    session_state를 사용하여 대화 이력을 관리하며,
    메시지 추가, 조회, 초기화 기능을 제공한다.
    """

    MAX_MESSAGES: int = 50
    MAX_CONTENT_LENGTH: int = 1000

    def __init__(self, session_state):
        """session_state를 사용하여 대화 이력 초기화.

        Args:
            session_state: Streamlit session_state 또는 dict-like 객체.
                           'messages' 키가 없으면 빈 리스트로 초기화한다.
        """
        self._session_state = session_state
        if "messages" not in self._session_state:
            self._session_state["messages"] = []

    def add_user_message(self, content: str) -> bool:
        """사용자 메시지를 대화 이력에 추가.

        빈 문자열, 공백만 있는 문자열, 1000자 초과 입력은 거부한다.

        Args:
            content: 사용자 입력 메시지 (최대 1000자)

        Returns:
            bool: 메시지 추가 성공 여부 (빈 메시지 또는 1000자 초과는 False)
        """
        if not isinstance(content, str):
            return False
        if not content.strip():
            return False
        if len(content) > self.MAX_CONTENT_LENGTH:
            return False

        self._session_state["messages"].append(
            {"role": "user", "content": content}
        )
        self._enforce_max_messages()
        return True

    def add_assistant_message(self, content: str) -> None:
        """AI 응답을 대화 이력에 추가.

        Args:
            content: AI가 생성한 응답 메시지
        """
        self._session_state["messages"].append(
            {"role": "assistant", "content": content}
        )
        self._enforce_max_messages()

    def get_history(self) -> list[dict]:
        """현재 대화 이력 반환.

        Returns:
            list[dict]: 대화 이력 리스트. 각 항목은 {"role": str, "content": str} 형태.
        """
        return list(self._session_state["messages"])

    def get_api_messages(self) -> list[dict]:
        """API 요청용 메시지 목록 반환 (최대 50개).

        Returns:
            list[dict]: API 요청에 포함할 메시지 목록 (최대 MAX_MESSAGES개).
        """
        messages = self._session_state["messages"]
        return list(messages[-self.MAX_MESSAGES:])

    def reset(self) -> None:
        """대화 이력 초기화."""
        self._session_state["messages"] = []

    def _enforce_max_messages(self) -> None:
        """최대 메시지 수 제한 적용.

        50개를 초과하면 가장 오래된 메시지부터 제거한다.
        """
        messages = self._session_state["messages"]
        if len(messages) > self.MAX_MESSAGES:
            self._session_state["messages"] = messages[-self.MAX_MESSAGES:]
