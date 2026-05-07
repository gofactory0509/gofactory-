"""ChatEngine 단위 테스트."""

import pytest

from chat_engine import ChatEngine


class FakeSessionState(dict):
    """Streamlit session_state를 모방하는 dict 기반 클래스."""
    pass


@pytest.fixture
def session_state():
    """빈 session_state를 반환하는 fixture."""
    return FakeSessionState()


@pytest.fixture
def engine(session_state):
    """ChatEngine 인스턴스를 반환하는 fixture."""
    return ChatEngine(session_state)


class TestInit:
    """ChatEngine 초기화 테스트."""

    def test_initializes_empty_messages(self, session_state):
        engine = ChatEngine(session_state)
        assert engine.get_history() == []

    def test_preserves_existing_messages(self):
        state = FakeSessionState(messages=[{"role": "user", "content": "hello"}])
        engine = ChatEngine(state)
        assert len(engine.get_history()) == 1


class TestAddUserMessage:
    """add_user_message 메서드 테스트."""

    def test_adds_valid_message(self, engine):
        result = engine.add_user_message("안녕하세요")
        assert result is True
        history = engine.get_history()
        assert len(history) == 1
        assert history[0] == {"role": "user", "content": "안녕하세요"}

    def test_rejects_empty_string(self, engine):
        result = engine.add_user_message("")
        assert result is False
        assert engine.get_history() == []

    def test_rejects_whitespace_only(self, engine):
        result = engine.add_user_message("   ")
        assert result is False
        assert engine.get_history() == []

    def test_rejects_tabs_and_newlines(self, engine):
        result = engine.add_user_message("\t\n  \r\n")
        assert result is False
        assert engine.get_history() == []

    def test_rejects_over_1000_chars(self, engine):
        long_message = "a" * 1001
        result = engine.add_user_message(long_message)
        assert result is False
        assert engine.get_history() == []

    def test_accepts_exactly_1000_chars(self, engine):
        message = "a" * 1000
        result = engine.add_user_message(message)
        assert result is True
        assert len(engine.get_history()) == 1

    def test_assigns_user_role(self, engine):
        engine.add_user_message("test")
        assert engine.get_history()[0]["role"] == "user"


class TestAddAssistantMessage:
    """add_assistant_message 메서드 테스트."""

    def test_adds_assistant_message(self, engine):
        engine.add_assistant_message("AI 응답입니다")
        history = engine.get_history()
        assert len(history) == 1
        assert history[0] == {"role": "assistant", "content": "AI 응답입니다"}

    def test_assigns_assistant_role(self, engine):
        engine.add_assistant_message("response")
        assert engine.get_history()[0]["role"] == "assistant"


class TestGetHistory:
    """get_history 메서드 테스트."""

    def test_returns_empty_list_initially(self, engine):
        assert engine.get_history() == []

    def test_returns_messages_in_order(self, engine):
        engine.add_user_message("first")
        engine.add_assistant_message("second")
        engine.add_user_message("third")
        history = engine.get_history()
        assert history[0]["content"] == "first"
        assert history[1]["content"] == "second"
        assert history[2]["content"] == "third"

    def test_returns_copy_not_reference(self, engine):
        engine.add_user_message("test")
        history = engine.get_history()
        history.append({"role": "user", "content": "injected"})
        assert len(engine.get_history()) == 1


class TestGetApiMessages:
    """get_api_messages 메서드 테스트."""

    def test_returns_all_messages_under_limit(self, engine):
        engine.add_user_message("hello")
        engine.add_assistant_message("hi")
        api_msgs = engine.get_api_messages()
        assert len(api_msgs) == 2

    def test_returns_max_50_messages(self, engine):
        for i in range(60):
            engine.add_user_message(f"msg {i}")
        api_msgs = engine.get_api_messages()
        assert len(api_msgs) <= 50


class TestReset:
    """reset 메서드 테스트."""

    def test_clears_all_messages(self, engine):
        engine.add_user_message("hello")
        engine.add_assistant_message("hi")
        engine.reset()
        assert engine.get_history() == []

    def test_allows_new_messages_after_reset(self, engine):
        engine.add_user_message("before")
        engine.reset()
        engine.add_user_message("after")
        history = engine.get_history()
        assert len(history) == 1
        assert history[0]["content"] == "after"


class TestEnforceMaxMessages:
    """_enforce_max_messages 메서드 테스트."""

    def test_removes_oldest_when_exceeding_limit(self, engine):
        for i in range(55):
            engine.add_user_message(f"message {i}")
        history = engine.get_history()
        assert len(history) == 50
        # 가장 오래된 5개 메시지가 제거되었는지 확인
        assert history[0]["content"] == "message 5"
        assert history[-1]["content"] == "message 54"

    def test_keeps_exactly_50_at_limit(self, engine):
        for i in range(50):
            engine.add_user_message(f"message {i}")
        assert len(engine.get_history()) == 50
