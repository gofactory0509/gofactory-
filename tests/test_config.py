"""ConfigManager 단위 테스트"""

import os

import pytest

from config import ConfigManager


class FakeSessionState(dict):
    """Streamlit session_state를 모방하는 dict 기반 클래스"""
    pass


class TestConfigManagerInit:
    """ConfigManager 초기화 테스트"""

    def test_init_without_env_var(self, monkeypatch):
        """환경 변수 없이 초기화하면 api_key가 None"""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        session = FakeSessionState()
        config = ConfigManager(session)
        assert session["api_key"] is None

    def test_init_with_env_var(self, monkeypatch):
        """환경 변수가 있으면 session_state에 로드"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-env-key")
        session = FakeSessionState()
        config = ConfigManager(session)
        assert session["api_key"] == "sk-test-env-key"

    def test_init_preserves_existing_session_key(self, monkeypatch):
        """session_state에 이미 api_key가 있으면 덮어쓰지 않음"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env-key")
        session = FakeSessionState({"api_key": "sk-session-key"})
        config = ConfigManager(session)
        assert session["api_key"] == "sk-session-key"


class TestGetApiKey:
    """get_api_key 메서드 테스트"""

    def test_returns_none_when_not_configured(self, monkeypatch):
        """API 키 미설정 시 None 반환"""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        session = FakeSessionState()
        config = ConfigManager(session)
        assert config.get_api_key() is None

    def test_returns_session_key(self, monkeypatch):
        """session_state에 저장된 키 반환"""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        session = FakeSessionState({"api_key": "sk-session-key"})
        config = ConfigManager(session)
        assert config.get_api_key() == "sk-session-key"

    def test_returns_env_key(self, monkeypatch):
        """환경 변수에서 API 키 로드"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env-key")
        session = FakeSessionState()
        config = ConfigManager(session)
        assert config.get_api_key() == "sk-env-key"

    def test_session_key_takes_priority_over_env(self, monkeypatch):
        """session_state 키가 환경 변수보다 우선"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env-key")
        session = FakeSessionState({"api_key": "sk-session-key"})
        config = ConfigManager(session)
        assert config.get_api_key() == "sk-session-key"

    def test_whitespace_only_key_returns_none(self, monkeypatch):
        """공백만 있는 키는 None 반환"""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        session = FakeSessionState({"api_key": "   "})
        config = ConfigManager(session)
        assert config.get_api_key() is None


class TestSetApiKey:
    """set_api_key 메서드 테스트"""

    def test_set_api_key_stores_in_session(self, monkeypatch):
        """set_api_key로 저장한 키가 session_state에 저장됨"""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        session = FakeSessionState()
        config = ConfigManager(session)
        config.set_api_key("sk-new-key")
        assert session["api_key"] == "sk-new-key"

    def test_set_api_key_overrides_env(self, monkeypatch):
        """set_api_key로 저장한 키가 환경 변수보다 우선"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env-key")
        session = FakeSessionState()
        config = ConfigManager(session)
        config.set_api_key("sk-user-key")
        assert config.get_api_key() == "sk-user-key"


class TestIsConfigured:
    """is_configured 메서드 테스트"""

    def test_not_configured_when_no_key(self, monkeypatch):
        """API 키 없으면 False"""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        session = FakeSessionState()
        config = ConfigManager(session)
        assert config.is_configured() is False

    def test_configured_with_session_key(self, monkeypatch):
        """session_state에 키가 있으면 True"""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        session = FakeSessionState({"api_key": "sk-valid-key"})
        config = ConfigManager(session)
        assert config.is_configured() is True

    def test_configured_with_env_key(self, monkeypatch):
        """환경 변수에 키가 있으면 True"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env-key")
        session = FakeSessionState()
        config = ConfigManager(session)
        assert config.is_configured() is True

    def test_not_configured_with_whitespace_key(self, monkeypatch):
        """공백만 있는 키는 미설정으로 판단"""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        session = FakeSessionState({"api_key": "  \t  "})
        config = ConfigManager(session)
        assert config.is_configured() is False
