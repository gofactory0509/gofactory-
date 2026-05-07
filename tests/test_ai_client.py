"""AIClient 단위 테스트.

mock을 사용하여 외부 API 호출 없이 AIClient의 오류 처리 및
정상 동작을 검증한다.
"""

from unittest.mock import MagicMock, patch

import pytest
from openai import APITimeoutError, AuthenticationError, APIError

from ai_client import AIClient


class TestAIClientInit:
    """AIClient 초기화 테스트."""

    def test_init_with_valid_api_key(self):
        """유효한 API 키로 초기화 성공."""
        with patch("ai_client.OpenAI") as mock_openai:
            client = AIClient("sk-valid-key-123")
            mock_openai.assert_called_once_with(
                api_key="sk-valid-key-123",
                base_url="https://api.deepseek.com",
                timeout=30,
                max_retries=3,
            )

    def test_init_with_none_api_key_raises_value_error(self):
        """None API 키로 초기화 시 ValueError 발생."""
        with pytest.raises(ValueError):
            AIClient(None)

    def test_init_with_empty_string_raises_value_error(self):
        """빈 문자열 API 키로 초기화 시 ValueError 발생."""
        with pytest.raises(ValueError):
            AIClient("")

    def test_init_with_whitespace_only_raises_value_error(self):
        """공백만 있는 API 키로 초기화 시 ValueError 발생."""
        with pytest.raises(ValueError):
            AIClient("   ")

    def test_init_with_tabs_only_raises_value_error(self):
        """탭만 있는 API 키로 초기화 시 ValueError 발생."""
        with pytest.raises(ValueError):
            AIClient("\t\t")


class TestValidateApiKey:
    """validate_api_key 정적 메서드 테스트."""

    def test_valid_key_returns_true(self):
        """유효한 API 키는 True 반환."""
        assert AIClient.validate_api_key("sk-valid-key") is True

    def test_none_returns_false(self):
        """None은 False 반환."""
        assert AIClient.validate_api_key(None) is False

    def test_empty_string_returns_false(self):
        """빈 문자열은 False 반환."""
        assert AIClient.validate_api_key("") is False

    def test_whitespace_only_returns_false(self):
        """공백만 있는 문자열은 False 반환."""
        assert AIClient.validate_api_key("   ") is False

    def test_tabs_and_newlines_returns_false(self):
        """탭과 개행만 있는 문자열은 False 반환."""
        assert AIClient.validate_api_key("\t\n") is False

    def test_key_with_leading_trailing_spaces_returns_true(self):
        """앞뒤 공백이 있지만 내용이 있는 키는 True 반환."""
        assert AIClient.validate_api_key("  sk-key  ") is True

    def test_non_string_returns_false(self):
        """문자열이 아닌 값은 False 반환."""
        assert AIClient.validate_api_key(12345) is False


class TestGenerateResponse:
    """generate_response 메서드 테스트."""

    @pytest.fixture
    def ai_client(self):
        """mock된 OpenAI 클라이언트를 가진 AIClient 인스턴스."""
        with patch("ai_client.OpenAI") as mock_openai:
            client = AIClient("sk-test-key")
            # mock_openai()가 반환하는 인스턴스를 client._client로 설정
            client._client = mock_openai.return_value
            yield client

    def test_normal_response(self, ai_client):
        """정상 응답 처리 테스트."""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "안녕하세요! 무엇을 도와드릴까요?"
        ai_client._client.chat.completions.create.return_value = mock_response

        messages = [{"role": "user", "content": "안녕하세요"}]
        result = ai_client.generate_response(messages)

        assert result == "안녕하세요! 무엇을 도와드릴까요?"
        ai_client._client.chat.completions.create.assert_called_once_with(
            model="deepseek-chat",
            messages=messages,
        )

    def test_timeout_error_handling(self, ai_client):
        """타임아웃 오류 처리 테스트 - TimeoutError로 변환."""
        ai_client._client.chat.completions.create.side_effect = APITimeoutError(
            request=MagicMock()
        )

        messages = [{"role": "user", "content": "안녕하세요"}]

        with pytest.raises(TimeoutError, match="응답 시간이 초과되었습니다"):
            ai_client.generate_response(messages)

    def test_authentication_error_handling(self, ai_client):
        """인증 오류 처리 테스트 - AuthenticationError 그대로 전파."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
        ai_client._client.chat.completions.create.side_effect = AuthenticationError(
            message="Invalid API key",
            response=mock_response,
            body={"error": {"message": "Invalid API key"}},
        )

        messages = [{"role": "user", "content": "안녕하세요"}]

        with pytest.raises(AuthenticationError):
            ai_client.generate_response(messages)

    def test_token_limit_exceeded_error(self, ai_client):
        """토큰 제한 초과 오류 처리 테스트 - APIError 전파."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {"message": "maximum context length exceeded"}
        }
        ai_client._client.chat.completions.create.side_effect = APIError(
            message="maximum context length exceeded",
            request=MagicMock(),
            body={"error": {"message": "maximum context length exceeded"}},
        )

        messages = [{"role": "user", "content": "매우 긴 대화"}]

        with pytest.raises(APIError):
            ai_client.generate_response(messages)

    def test_general_api_error(self, ai_client):
        """일반 API 오류 처리 테스트 - APIError 전파."""
        ai_client._client.chat.completions.create.side_effect = APIError(
            message="Internal server error",
            request=MagicMock(),
            body={"error": {"message": "Internal server error"}},
        )

        messages = [{"role": "user", "content": "안녕하세요"}]

        with pytest.raises(APIError):
            ai_client.generate_response(messages)

    def test_multiple_messages_in_conversation(self, ai_client):
        """여러 메시지가 포함된 대화 이력으로 응답 생성."""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "좋은 질문이네요!"
        ai_client._client.chat.completions.create.return_value = mock_response

        messages = [
            {"role": "user", "content": "안녕하세요"},
            {"role": "assistant", "content": "안녕하세요!"},
            {"role": "user", "content": "오늘 뭐 할까?"},
        ]
        result = ai_client.generate_response(messages)

        assert result == "좋은 질문이네요!"
        ai_client._client.chat.completions.create.assert_called_once_with(
            model="deepseek-chat",
            messages=messages,
        )
