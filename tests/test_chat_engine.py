"""대화 엔진 테스트."""

from chat_engine import ChatEngine


def test_add_user_message():
    state = {}
    engine = ChatEngine(state)
    result = engine.add_user_message("안녕하세요")
    assert result is True
    assert len(engine.get_history()) == 1
    assert engine.get_history()[0]["role"] == "user"


def test_add_model_message():
    state = {}
    engine = ChatEngine(state)
    engine.add_model_message("반갑습니다")
    assert len(engine.get_history()) == 1
    assert engine.get_history()[0]["role"] == "model"


def test_reset():
    state = {}
    engine = ChatEngine(state)
    engine.add_user_message("테스트")
    engine.reset()
    assert len(engine.get_history()) == 0


def test_empty_message_rejected():
    state = {}
    engine = ChatEngine(state)
    result = engine.add_user_message("")
    assert result is False
    assert len(engine.get_history()) == 0
