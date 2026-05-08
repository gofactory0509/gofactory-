"""AI 클라이언트 테스트."""

from ai_client import AIClient


def test_validate_api_key_valid():
    assert AIClient.validate_api_key("AIzaSyTest123") is True


def test_validate_api_key_empty():
    assert AIClient.validate_api_key("") is False


def test_validate_api_key_none():
    assert AIClient.validate_api_key(None) is False


def test_validate_api_key_whitespace():
    assert AIClient.validate_api_key("   ") is False
