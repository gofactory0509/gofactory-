"""AI 모델 클라이언트 모듈.

Groq API와의 통신을 담당하며, OpenAI 호환 API를 사용한다.
30초 타임아웃, 인증 오류, 토큰 제한 초과 등의 오류를 처리한다.
"""

from openai import OpenAI, APITimeoutError, AuthenticationError, APIError


class AIClient:
    """Groq AI 모델 클라이언트 (OpenAI 호환 API).

    OpenAI Python SDK를 사용하여 Groq API와 통신한다.
    base_url을 Groq 엔드포인트로 지정하여 호환 API를 활용한다.
    """

    BASE_URL: str = "https://api.groq.com/openai/v1"
    MODEL_NAME: str = "llama-3.3-70b-versatile"
    TIMEOUT_SECONDS: int = 30
    MAX_RETRIES: int = 3

    def __init__(self, api_key: str):
        """OpenAI 호환 클라이언트 초기화.

        Args:
            api_key: DeepSeek API 인증 키

        Raises:
            ValueError: api_key가 빈 문자열이거나 None이거나 공백만 있는 경우
        """
        if not self.validate_api_key(api_key):
            raise ValueError(
                "API 키가 유효하지 않습니다. 빈 문자열이거나 None일 수 없습니다."
            )

        self._client = OpenAI(
            api_key=api_key,
            base_url=self.BASE_URL,
            timeout=self.TIMEOUT_SECONDS,
            max_retries=self.MAX_RETRIES,
        )

    def generate_response(self, messages: list[dict]) -> str:
        """AI 응답 생성.

        Args:
            messages: OpenAI 형식의 메시지 목록
                      [{"role": "user"|"assistant", "content": str}, ...]

        Returns:
            str: AI 생성 응답 텍스트

        Raises:
            TimeoutError: 30초 이내 응답 없음
            AuthenticationError: API 키 인증 실패
            APIError: 기타 API 오류 (토큰 제한 초과 등)
        """
        try:
            response = self._client.chat.completions.create(
                model=self.MODEL_NAME,
                messages=messages,
            )
            return response.choices[0].message.content

        except APITimeoutError as e:
            raise TimeoutError(
                "응답 시간이 초과되었습니다. 다시 시도해주세요."
            ) from e

        except AuthenticationError:
            raise

        except APIError:
            raise

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """API 키 형식 유효성 검증 (빈 문자열 체크).

        Args:
            api_key: 검증할 API 키 문자열

        Returns:
            bool: API 키가 유효하면 True, 아니면 False
        """
        if api_key is None:
            return False
        if not isinstance(api_key, str):
            return False
        if not api_key.strip():
            return False
        return True
