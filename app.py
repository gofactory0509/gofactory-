"""GoFactory 메인 Streamlit 애플리케이션.

GoFactory 챗봇의 진입점으로, 전체 UI 레이아웃과 이벤트 루프를 관리한다.
DeepSeek 무료 AI 모델을 OpenAI 호환 API를 통해 연동하며,
사용자는 웹 브라우저에서 별도 설치 없이 AI와 대화할 수 있다.
"""

import streamlit as st
from openai import AuthenticationError, APIError

from chat_engine import ChatEngine
from ai_client import AIClient
from config import ConfigManager


def init_session_state():
    """session_state 초기화.

    messages, api_key, is_generating 키가 없으면 기본값으로 초기화한다.
    """
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "api_key" not in st.session_state:
        st.session_state["api_key"] = None
    if "is_generating" not in st.session_state:
        st.session_state["is_generating"] = False


def render_sidebar(config: ConfigManager, engine: ChatEngine):
    """사이드바 렌더링: API 키 입력 및 새 대화 버튼.

    Args:
        config: 설정 관리자 인스턴스
        engine: 대화 관리 엔진 인스턴스
    """
    with st.sidebar:
        st.header("⚙️ 설정")

        # API 키 입력 필드 (password 타입)
        api_key_input = st.text_input(
            "Groq API 키",
            type="password",
            value=config.get_api_key() or "",
            placeholder="gsk_...",
            help="Groq API 키를 입력하세요. 키는 세션 동안만 유지됩니다.",
        )

        # API 키가 변경되면 세션에 저장
        if api_key_input and api_key_input.strip():
            config.set_api_key(api_key_input.strip())

        # 새 대화 버튼
        if st.button("🔄 새 대화", use_container_width=True):
            engine.reset()
            st.session_state["is_generating"] = False
            st.rerun()


def render_chat_history(engine: ChatEngine):
    """대화 이력을 채팅 인터페이스에 표시.

    Args:
        engine: 대화 관리 엔진 인스턴스
    """
    for message in engine.get_history():
        role = message["role"]
        avatar = "👤" if role == "user" else "🏭"
        with st.chat_message(role, avatar=avatar):
            st.markdown(message["content"])


def handle_user_input(user_input: str, config: ConfigManager, engine: ChatEngine):
    """사용자 메시지 입력 처리 및 AI 응답 생성.

    Args:
        user_input: 사용자가 입력한 메시지
        config: 설정 관리자 인스턴스
        engine: 대화 관리 엔진 인스턴스
    """
    # 빈 메시지 차단
    if not user_input or not user_input.strip():
        return

    # 입력 길이 제한 (1000자)
    if len(user_input) > 1000:
        st.error("📝 메시지는 1000자 이내로 입력해주세요.")
        return

    # API 키 미설정 시 차단
    if not config.is_configured():
        st.warning("⚠️ 사이드바에서 API 키를 입력해주세요.")
        return

    # 사용자 메시지 추가
    engine.add_user_message(user_input)

    # 사용자 메시지 즉시 표시
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    # AI 응답 생성
    try:
        st.session_state["is_generating"] = True
        with st.spinner("생각 중..."):
            ai_client = AIClient(config.get_api_key())
            response = ai_client.generate_response(engine.get_api_messages())
            engine.add_assistant_message(response)

        # AI 응답 표시
        with st.chat_message("assistant", avatar="🏭"):
            st.markdown(response)

    except TimeoutError:
        st.error("⏱️ 응답 시간이 초과되었습니다. 다시 시도해주세요.")
    except AuthenticationError:
        st.error("🔑 API 키가 유효하지 않습니다. 사이드바에서 확인해주세요.")
    except APIError as e:
        # 토큰 제한 초과 등 API 오류 처리
        error_message = str(e).lower()
        if "token" in error_message or "length" in error_message:
            st.error("📝 대화가 너무 길어졌습니다. '새 대화'를 시작해주세요.")
        else:
            st.error("❌ 응답 생성에 실패했습니다. 잠시 후 다시 시도해주세요.")
    except Exception:
        st.error("❌ 응답 생성에 실패했습니다. 잠시 후 다시 시도해주세요.")
    finally:
        st.session_state["is_generating"] = False


def main():
    """GoFactory 메인 애플리케이션."""
    # 페이지 설정
    st.set_page_config(page_title="GoFactory", page_icon="🏭")

    # session_state 초기화
    init_session_state()

    # 모듈 초기화
    config = ConfigManager(st.session_state)
    engine = ChatEngine(st.session_state)

    # 페이지 헤더
    st.title("🏭 GoFactory")
    st.caption("Groq AI 기반 개인 맞춤형 챗봇입니다. 자유롭게 대화해보세요.")

    # 사이드바 렌더링
    render_sidebar(config, engine)

    # 대화 이력 표시
    render_chat_history(engine)

    # 메시지 입력
    user_input = st.chat_input("메시지를 입력하세요...")

    if user_input:
        handle_user_input(user_input, config, engine)


if __name__ == "__main__":
    main()
