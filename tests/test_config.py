"""설정 관리자 테스트."""

import os
from config import ConfigManager


def test_env_key_name():
    assert ConfigManager.ENV_KEY_NAME == "GEMINI_API_KEY"


def test_get_api_key_from_session():
    state = {"api_key": "test_key_123"}
    config = ConfigManager(state)
    assert config.get_api_key() == "test_key_123"


def test_is_configured_true():
    state = {"api_key": "test_key_123"}
    config = ConfigManager(state)
    assert config.is_configured() is True


def test_is_configured_false():
    state = {}
    # Clear env var if set
    os.environ.pop("GEMINI_API_KEY", None)
    config = ConfigManager(state)
    assert config.is_configured() is False


def test_set_api_key():
    state = {}
    os.environ.pop("GEMINI_API_KEY", None)
    config = ConfigManager(state)
    config.set_api_key("new_key")
    assert config.get_api_key() == "new_key"
