"""설정 관리 모듈

API 키 및 앱 설정을 관리한다.
설정 우선순위:
1. 사이드바에서 사용자가 직접 입력한 API 키 (session_state)
2. 환경 변수 (GEMINI_API_KEY)
3. .env 파일
"""

import os

from dotenv import load_dotenv


class ConfigManager:
    """설정 관리자

    환경 변수, .env 파일, session_state를 통해 API 키를 관리한다.
    """

    ENV_KEY_NAME = "GEMINI_API_KEY"
    SESSION_KEY_NAME = "api_key"

    def __init__(self, session_state):
        """환경 변수 또는 session_state에서 설정 로드

        Args:
            session_state: Streamlit session_state 객체 (dict-like)
        """
        self._session_state = session_state

        # .env 파일에서 환경 변수 로드 (기존 환경 변수를 덮어쓰지 않음)
        load_dotenv(override=False)

        # session_state에 api_key가 없으면 환경 변수에서 로드
        if self.SESSION_KEY_NAME not in self._session_state:
            env_key = os.environ.get(self.ENV_KEY_NAME)
            if env_key and env_key.strip():
                self._session_state[self.SESSION_KEY_NAME] = env_key
            else:
                self._session_state[self.SESSION_KEY_NAME] = None

    def get_api_key(self) -> str | None:
        """현재 설정된 API 키 반환 (없으면 None)

        Returns:
            str | None: 설정된 API 키 또는 None
        """
        # session_state에 저장된 키가 있으면 우선 반환
        session_key = self._session_state.get(self.SESSION_KEY_NAME)
        if session_key and session_key.strip():
            return session_key

        # 환경 변수에서 확인 (.env 파일 포함)
        env_key = os.environ.get(self.ENV_KEY_NAME)
        if env_key and env_key.strip():
            return env_key

        return None

    def set_api_key(self, api_key: str) -> None:
        """API 키를 세션에 저장

        Args:
            api_key: 저장할 API 키 문자열
        """
        self._session_state[self.SESSION_KEY_NAME] = api_key

    def is_configured(self) -> bool:
        """API 키가 설정되어 있는지 확인

        Returns:
            bool: API 키가 유효하게 설정되어 있으면 True
        """
        api_key = self.get_api_key()
        return api_key is not None and bool(api_key.strip())
