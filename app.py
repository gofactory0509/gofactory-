# -*- coding: utf-8 -*-
"""Go터뷰 챗봇 메인 애플리케이션."""

import base64
import streamlit as st
import os
import re
import random
from datetime import date
from pathlib import Path


LOGO_PATH = Path(__file__).parent / "assets" / "logo.png"


def _logo_data_uri() -> str | None:
    """로고 이미지를 data: URI로 반환. 파일 없으면 None."""
    if not LOGO_PATH.exists():
        return None
    return "data:image/png;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode()

import pandas as pd

from ai_client import AIClient, parse_detail_scores
from config import ConfigManager
from database import InterviewDB, JOB_BUSINESS_UNITS, JOB_DESCRIPTIONS


# 삼성전자 DS부문 '26상 공채 직무기술서 기준 10개 직무
JOB_FIELDS = list(JOB_BUSINESS_UNITS.keys())
INTERVIEW_TYPES = ["직무면접", "인성면접", "자소서기반면접"]

# 오늘의 명언 (취업 준비생을 위한 동기부여 명언 30+)
DAILY_QUOTES = [
    "준비된 자에게 기회는 찾아온다.",
    "면접은 나를 보여주는 무대다.",
    "실패는 성공의 연습이다.",
    "꾸준함이 재능을 이긴다.",
    "오늘의 연습이 내일의 자신감이 된다.",
    "완벽한 답변보다 진솔한 답변이 낫다.",
    "긴장은 준비가 부족할 때 찾아온다.",
    "작은 성장도 성장이다.",
    "포기하지 않는 한 실패는 없다.",
    "나를 가장 잘 아는 사람은 나 자신이다.",
    "매일 1%씩 성장하면 1년 후 37배가 된다.",
    "면접관도 사람이다. 대화하듯 임하자.",
    "경험을 이야기로 만들 수 있는 사람이 합격한다.",
    "자신감은 준비에서 나온다.",
    "오늘 흘린 땀이 내일의 합격 통보가 된다.",
    "부족함을 아는 것이 성장의 시작이다.",
    "질문의 의도를 파악하는 것이 절반의 답이다.",
    "나만의 강점을 명확히 말할 수 있어야 한다.",
    "실전처럼 연습하고, 연습처럼 실전에 임하자.",
    "좋은 답변은 구체적인 경험에서 나온다.",
    "합격은 운이 아니라 준비의 결과다.",
    "지금 이 순간의 노력이 미래를 바꾼다.",
    "두려움은 행동으로 극복된다.",
    "피드백은 성장의 가장 빠른 길이다.",
    "남과 비교하지 말고 어제의 나와 비교하자.",
    "면접은 끝이 아니라 시작이다.",
    "성실함은 어떤 스펙보다 강력하다.",
    "한 번 더 연습하는 사람이 결국 이긴다.",
    "나의 이야기에 확신을 가지자.",
    "불합격은 방향을 알려주는 나침반이다.",
    "지금 힘든 만큼 나중에 빛날 것이다.",
    "목표가 명확하면 길은 보인다.",
    "작은 습관이 큰 결과를 만든다.",
]


CUSTOM_CSS = """
<style>
    /* OS 다크모드와 무관하게 light 스킴 잠금 */
    :root { color-scheme: light; }
    .stApp {
        background: linear-gradient(180deg, #f8f9fc 0%, #ffffff 100%);
        color-scheme: light;
    }

    /* 다크모드에서 흰 텍스트가 흰 배경에 묻히는 문제 방지 — 텍스트 색상 명시 */
    .stApp, .stApp p, .stApp span, .stApp div,
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
    .stApp label, .stApp .stMarkdown { color: #2d3748; }
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div, section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] .stMarkdown { color: #2d3748; }
    /* st.caption 등 회색 텍스트 */
    .stApp small, section[data-testid="stSidebar"] small { color: #718096; }
    /* 입력 박스 — 다크모드에서 검정 배경 되는 것 방지 */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #2d3748 !important;
    }

    /* 헤더 배너 */
    .header-banner {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.4rem 1.8rem;
        border-radius: 14px;
        margin-bottom: 1.5rem;
        color: white;
        display: flex;
        align-items: center;
        gap: 1.1rem;
        box-shadow: 0 4px 12px rgba(102,126,234,0.18);
    }
    .header-banner .header-logo {
        height: 64px;
        width: 64px;
        object-fit: contain;
        background: white;
        border-radius: 14px;
        padding: 6px;
        flex-shrink: 0;
    }
    .header-banner .header-text { flex: 1; }
    .header-banner h1 {
        margin: 0;
        font-size: 1.7rem;
        font-weight: 700;
        color: white !important;
        letter-spacing: -0.02em;
    }
    .header-banner p {
        margin: 0.3rem 0 0 0;
        font-size: 0.92rem;
        opacity: 0.92;
        color: #e8e8ff !important;
    }

    /* 명언 카드 */
    .quote-card {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        padding: 1.2rem 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #f093fb;
    }
    .quote-card p {
        margin: 0;
        font-size: 1rem;
        color: #4a3728;
        font-weight: 500;
        line-height: 1.6;
    }

    /* 피드백 카드 */
    .feedback-card {
        background: #f0f4ff;
        border: 1px solid #d4deff;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .feedback-card h4 {
        color: #4a5568;
        margin-top: 0;
        margin-bottom: 0.8rem;
    }

    /* 통계 카드 */
    .stats-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stats-card .stat-number {
        font-size: 1.8rem;
        font-weight: 700;
        color: #667eea;
    }
    .stats-card .stat-label {
        font-size: 0.85rem;
        color: #718096;
        margin-top: 0.3rem;
    }

    /* 질문 박스 */
    .question-box {
        background: white;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #667eea;
        border-radius: 8px;
        padding: 1.2rem 1.5rem;
        margin: 1rem 0;
        font-size: 1.05rem;
        line-height: 1.6;
    }

    /* 동기부여 메시지 */
    .motivation-msg {
        background: linear-gradient(135deg, #e0f7fa 0%, #e8f5e9 100%);
        border-radius: 8px;
        padding: 0.8rem 1.2rem;
        margin-top: 1rem;
        font-size: 0.9rem;
        color: #2e7d32;
    }

    /* 사이드바 스타일 */
    section[data-testid="stSidebar"] {
        background: #f7f8fc;
    }

    /* 회사 인재상 배너 (면접 화면 맨 위) */
    .company-banner {
        background: linear-gradient(135deg, #ebf4ff 0%, #e9d8fd 100%);
        border-left: 4px solid #667eea;
        border-radius: 12px;
        padding: 1rem 1.3rem;
        margin: 0.6rem 0 1.2rem;
        box-shadow: 0 2px 6px rgba(102,126,234,0.08);
    }
    .company-banner .cb-name {
        font-size: 1.05rem; font-weight: 700; color: #2d3748;
        margin-bottom: 0.35rem; display: flex; align-items: baseline; gap: 0.4rem;
        flex-wrap: wrap;
    }
    .company-banner .cb-industry {
        font-size: 0.78rem; color: #718096; font-weight: 500;
        background: white; padding: 0.15rem 0.55rem; border-radius: 999px;
    }
    .company-banner .cb-talent {
        font-size: 0.95rem; color: #2d3748; line-height: 1.55;
        font-weight: 500;
    }
    .company-banner .cb-focus {
        font-size: 0.85rem; color: #667eea; margin-top: 0.4rem;
        font-weight: 600;
    }
</style>
"""

# 피드백 후 동기부여 메시지
MOTIVATION_MESSAGES = [
    "한 걸음 더 성장했습니다. 꾸준히 연습하면 반드시 좋은 결과가 있을 거예요.",
    "오늘의 연습이 내일의 합격으로 이어집니다. 잘하고 있어요.",
    "피드백을 받아들이는 자세가 이미 훌륭합니다. 계속 도전하세요.",
    "매번 조금씩 나아지고 있습니다. 그 과정을 믿으세요.",
    "연습은 배신하지 않습니다. 오늘도 수고했어요.",
]


class _ByokAwareClient:
    """BYOK 우선 + AIClient 폴백 어댑터.

    Streamlit 측에서 ``get_ai_client()`` 가 반환하는 객체. 호출자 코드를 바꾸지
    않고도 다음 동작을 보장한다:

    - 세션에 OpenRouter 키가 있으면 :meth:`generate_question`/
      :meth:`evaluate_answer` 는 :class:`backend.services.llm_router.LLMRouter`
      로 라우팅 (Bedrock 또는 OpenRouter).
    - 키가 없거나 기타 메서드(``transcribe_audio``, ``generate_targeted_question``
      등)는 기존 AIClient(Gemini/Groq) 에 위임 — backward compatible.

    LLMRouter 와 AIClient 의 ``generate_question`` 시그니처가 호환되도록
    LLMRouter 측을 보강했으므로 직접 위임이 가능하다.
    """

    def __init__(self, primary: AIClient, router: "LLMRouter | None"):
        self._primary = primary
        self._router = router

    # 위임이 필요한 두 메서드만 LLMRouter 경로로 분기
    def generate_question(self, *args, **kwargs):
        if self._router is not None:
            return self._router.generate_question(*args, **kwargs)
        return self._primary.generate_question(*args, **kwargs)

    def evaluate_answer(self, *args, **kwargs):
        if self._router is not None:
            return self._router.evaluate_answer(*args, **kwargs)
        return self._primary.evaluate_answer(*args, **kwargs)

    def backend_name(self) -> str:
        """현재 어떤 백엔드로 라우팅 중인지."""
        if self._router is not None:
            return self._router.backend_name()
        return "gemini"  # legacy AIClient (Gemini + Groq fallback)

    # 그 외 모든 속성/메서드는 primary(AIClient)로 위임 — backward compat
    def __getattr__(self, name):
        return getattr(self._primary, name)


def get_ai_client(config: ConfigManager):
    """AI 클라이언트 팩토리 (BYOK 인지 어댑터 반환).

    기본은 LLMRouter — BYOK OpenRouter 키 있으면 OpenRouter, 없으면 Bedrock Haiku.
    Gemini/Groq는 ``transcribe_audio`` 등 legacy 메서드 폴백용으로만 유지.
    """
    gemini_key = config.get_api_key()
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key:
        try:
            groq_key = st.secrets.get("GROQ_API_KEY", "")
        except Exception:
            groq_key = ""

    primary = AIClient(gemini_key=gemini_key, groq_key=groq_key)

    or_key = (st.session_state.get("openrouter_key", "") or "").strip()
    or_model = (st.session_state.get("openrouter_model", "") or "").strip()

    # LLMRouter는 키가 비어 있어도 Bedrock으로 자동 폴백 — 항상 만든다.
    # 라우터 초기화 자체가 실패할 때만 primary(Gemini/Groq) 로 떨어진다.
    router = None
    try:
        from backend.services.llm_router import LLMRouter
        router = LLMRouter(
            user_openrouter_key=or_key or None,
            user_model=or_model or None,
        )
    except Exception:
        router = None

    return _ByokAwareClient(primary, router)


def init_session_state():
    defaults = {
        "api_key": None,
        "current_question": None,
        "job_field": None,
        "business_unit": None,
        "interview_type": "직무면접",
        "company": "",
        "interview_active": False,
        "feedback": None,
        "question_count": 0,
        "show_records": False,
        "show_resume": False,
        "show_feedback_form": False,
        "show_data_dashboard": False,
        "show_weakness_page": False,
        # BYOK: 사용자 OpenRouter 키/모델 (세션 한정 — 종료 시 사라짐)
        "openrouter_key": "",
        "openrouter_model": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_daily_quote() -> str:
    """오늘의 명언 반환 (날짜 기반 시드로 하루 동안 동일한 명언)."""
    today = date.today()
    seed = today.year * 10000 + today.month * 100 + today.day
    rng = random.Random(seed)
    return rng.choice(DAILY_QUOTES)


def _render_byok_sidebar() -> None:
    """OpenRouter BYOK 입력 섹션을 사이드바에 렌더한다.

    세션 상태:
        - ``st.session_state["openrouter_key"]`` : 입력된 키 (없으면 빈 문자열)
        - ``st.session_state["openrouter_model"]`` : 선택된 모델 ID
        - ``st.session_state["openrouter_validated"]`` : 검증 결과 dict (옵션)

    이 함수는 키 원문을 UI에 다시 노출하지 않는다 (type="password").
    검증 시에만 :func:`backend.services.key_validator.validate_openrouter_key`
    를 호출하고, 응답에는 마스킹된 미리보기만 포함한다.
    """
    from backend.services.key_validator import validate_openrouter_key, mask_key
    from backend.services.openrouter_client import DEFAULT_MODEL, SUPPORTED_MODELS

    with st.expander("🔑 OpenRouter API 키 (선택)", expanded=False):
        st.caption(
            "키 없이도 무료 사용 가능. 본인 키 사용 시 GPT/Claude/Gemini 등 모델을 자유롭게 선택할 수 있습니다."
        )
        or_key = st.text_input(
            "API 키",
            value=st.session_state.get("openrouter_key", "") or "",
            type="password",
            placeholder="sk-or-v1-...",
            help="없으면 서비스 기본 백엔드 사용. 본인 키 입력 시 모델 선택 가능.",
            key="byok_key_input",
        )
        # 세션에 즉시 반영 (입력 변경 시)
        st.session_state["openrouter_key"] = (or_key or "").strip()

        if st.session_state["openrouter_key"]:
            model_ids = list(SUPPORTED_MODELS.keys())
            default_idx = model_ids.index(DEFAULT_MODEL) if DEFAULT_MODEL in model_ids else 0
            current_model = st.session_state.get("openrouter_model") or DEFAULT_MODEL
            if current_model in model_ids:
                default_idx = model_ids.index(current_model)
            chosen = st.selectbox(
                "모델",
                model_ids,
                index=default_idx,
                format_func=lambda m: SUPPORTED_MODELS[m],
                key="byok_model_select",
            )
            st.session_state["openrouter_model"] = chosen

            if st.button("키 검증", key="byok_validate_btn", use_container_width=True):
                with st.spinner("OpenRouter 키를 검증 중..."):
                    result = validate_openrouter_key(st.session_state["openrouter_key"])
                st.session_state["openrouter_validated"] = result
                if result.get("valid"):
                    parts = ["✅ 키 유효"]
                    if result.get("label"):
                        parts.append(f"라벨: {result['label']}")
                    if result.get("credit_left") is not None:
                        parts.append(f"잔액: ${result['credit_left']:.2f}")
                    if result.get("models_count") is not None:
                        parts.append(f"모델: {result['models_count']}개")
                    parts.append(f"({mask_key(st.session_state['openrouter_key'])})")
                    st.success(" · ".join(parts))
                else:
                    st.error(f"❌ {result.get('error', '검증 실패')}")
        else:
            st.session_state["openrouter_model"] = ""
            st.session_state.pop("openrouter_validated", None)

        st.caption(
            "⚠️ 키는 서버를 거치지만 저장되지 않습니다. "
            "[openrouter.ai/keys](https://openrouter.ai/keys) 에서 발급."
        )

        # 현재 사용 백엔드 배지
        if st.session_state.get("openrouter_key"):
            st.caption("📍 현재 백엔드: 🔑 OpenRouter (BYOK)")
        else:
            st.caption("📍 현재 백엔드: 📡 AWS Bedrock Haiku · 키 입력 없이 바로 사용")


def render_sidebar(config: ConfigManager, db: InterviewDB):
    with st.sidebar:
        st.header("면접 설정")

        # 기본 백엔드는 AWS Bedrock Haiku — 키 없이 즉시 사용 가능.
        # 사용자 키는 BYOK(OpenRouter) 또는 legacy Gemini로 선택 입력.
        _render_byok_sidebar()

        if not config.is_configured():
            with st.expander("🔧 Gemini API 키 (선택 · 음성 전사 등)", expanded=False):
                api_key_input = st.text_input(
                    "Gemini API 키",
                    type="password",
                    placeholder="AIzaSy...",
                    help="입력하지 않아도 면접은 Bedrock Haiku로 정상 진행됩니다.",
                )
                if api_key_input and api_key_input.strip():
                    config.set_api_key(api_key_input.strip())
                    st.rerun()

        st.subheader("직무 선택")
        selected_job = st.selectbox(
            "면접 직무를 선택하세요",
            JOB_FIELDS,
            index=0,
            label_visibility="collapsed",
            help="삼성전자 DS부문 '26상 공채 직무기술서 기준",
        )
        if selected_job and JOB_DESCRIPTIONS.get(selected_job):
            st.caption(JOB_DESCRIPTIONS[selected_job])

        # 사업부 선택 (해당 직무가 모집되는 사업부 중에서)
        available_units = JOB_BUSINESS_UNITS.get(selected_job, [])
        selected_business_unit = None
        if available_units:
            st.subheader("사업부 선택")
            if len(available_units) == 1:
                selected_business_unit = available_units[0]
                st.caption(f"이 직무는 **{selected_business_unit}** 에서 모집됩니다")
            else:
                selected_business_unit = st.radio(
                    "면접 대상 사업부",
                    available_units,
                    index=0,
                    label_visibility="collapsed",
                    help="같은 직무라도 사업부에 따라 세부 업무가 다릅니다",
                )

        # 면접 유형 선택
        st.subheader("면접 유형")
        selected_type = st.radio(
            "면접 유형을 선택하세요",
            INTERVIEW_TYPES,
            index=0,
            label_visibility="collapsed",
            help="자소서기반면접: 자소서를 먼저 등록해야 합니다",
        )

        # 회사 선택 (선택사항)
        st.subheader("지원 회사 (선택)")
        cached_companies = db.list_cached_companies()
        cached_names = [c["name"] for c in cached_companies]
        company_options = ["(선택 안 함)"] + cached_names + ["기타 (직접 입력)"]
        company_choice = st.selectbox(
            "회사명",
            company_options,
            index=0,
            label_visibility="collapsed",
            help=(
                "캐시 회사를 선택하면 인재상·주력사업·최신트렌드가 면접에 자동 반영됩니다. "
                "드롭다운에서 타이핑하면 검색됩니다."
            ),
        )
        selected_company = ""
        if company_choice == "기타 (직접 입력)":
            custom = st.text_input(
                "회사명 직접 입력",
                placeholder="예: LG이노텍, 네이버, 키엔스...",
                label_visibility="visible",
            )
            selected_company = custom.strip() if custom else ""
            if selected_company:
                st.caption("ℹ️ 캐시에 없는 회사 (LLM 일반 지식으로 면접 진행)")
        elif company_choice != "(선택 안 함)":
            selected_company = company_choice
            _preview = db.get_company_info(selected_company)
            if _preview:
                st.caption(f"📚 캐시 적중 — {_preview['industry']}")

        st.divider()
        if st.button("면접 시작", use_container_width=True, type="primary"):
            if selected_job is None:
                st.error("직무명을 입력해주세요.")
            elif selected_type == "자소서기반면접" and not db.get_resume(selected_job):
                st.error("자소서를 먼저 등록해주세요. 아래 '자소서 관리' 버튼을 눌러주세요.")
            else:
                st.session_state["job_field"] = selected_job
                st.session_state["business_unit"] = selected_business_unit
                st.session_state["interview_type"] = selected_type
                st.session_state["company"] = selected_company
                st.session_state["interview_active"] = True
                st.session_state["current_question"] = None
                st.session_state["feedback"] = None
                st.session_state["question_count"] = 0
                st.session_state["show_records"] = False
                st.session_state["show_resume"] = False
                st.session_state["show_feedback_form"] = False
                st.session_state["show_data_dashboard"] = False
                st.session_state["show_weakness_page"] = False
                st.rerun()

        if st.session_state.get("interview_active"):
            if st.button("면접 종료", use_container_width=True):
                st.session_state["interview_active"] = False
                st.session_state["current_question"] = None
                st.session_state["feedback"] = None
                st.session_state.pop("weakness_target", None)
                st.rerun()

        st.divider()
        st.subheader("메뉴")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📄 자소서", use_container_width=True):
                st.session_state["show_resume"] = True
                st.session_state["show_records"] = False
                st.session_state["show_feedback_form"] = False
                st.session_state["show_data_dashboard"] = False
                st.session_state["show_weakness_page"] = False
                st.session_state["interview_active"] = False
                st.rerun()
        with col2:
            if st.button("📋 기록", use_container_width=True):
                st.session_state["show_records"] = True
                st.session_state["show_resume"] = False
                st.session_state["show_feedback_form"] = False
                st.session_state["show_data_dashboard"] = False
                st.session_state["show_weakness_page"] = False
                st.session_state["interview_active"] = False
                st.rerun()

        col3, col4 = st.columns(2)
        with col3:
            if st.button("💬 피드백", use_container_width=True):
                st.session_state["show_feedback_form"] = True
                st.session_state["show_records"] = False
                st.session_state["show_resume"] = False
                st.session_state["show_data_dashboard"] = False
                st.session_state["show_weakness_page"] = False
                st.session_state["interview_active"] = False
                st.rerun()
        with col4:
            if st.button("📊 대시보드", use_container_width=True):
                st.session_state["show_data_dashboard"] = True
                st.session_state["show_records"] = False
                st.session_state["show_resume"] = False
                st.session_state["show_feedback_form"] = False
                st.session_state["show_weakness_page"] = False
                st.session_state["interview_active"] = False
                st.rerun()

        if st.button("🎯 약점 집중 연습", use_container_width=True):
            st.session_state["show_weakness_page"] = True
            st.session_state["show_data_dashboard"] = False
            st.session_state["show_records"] = False
            st.session_state["show_resume"] = False
            st.session_state["show_feedback_form"] = False
            st.session_state["interview_active"] = False
            st.rerun()

        st.divider()
        record_count = db.get_record_count()
        st.caption(f"총 {record_count}건 면접 기록 저장됨")


def extract_score(feedback: str) -> int | None:
    """AI 피드백 텍스트에서 총점(100점 만점)을 추출."""
    # "[점수] ... 총점: 75/100" 패턴 매칭
    patterns = [
        r'총점\s*[:：]\s*(\d+)\s*/\s*100',
        r'총점\s*(\d+)\s*/\s*100',
        r'(\d+)\s*/\s*100',
    ]
    for pattern in patterns:
        match = re.search(pattern, feedback)
        if match:
            score = int(match.group(1))
            if 0 <= score <= 100:
                return score
    return None


def extract_detail_scores(feedback: str) -> dict:
    """AI 피드백에서 항목별 점수를 추출 (ai_client.parse_detail_scores 위임).

    None 값은 호환을 위해 반환 dict에서 제거하여, 기존 .get(label, 0) 호출이
    그대로 동작하도록 한다.
    """
    raw = parse_detail_scores(feedback)
    return {k: v for k, v in raw.items() if v is not None}


def render_resume_page(db: InterviewDB):
    """자소서 관리 페이지."""
    st.subheader("📄 자소서 관리")
    st.caption("자소서를 등록하면 자소서 기반 맞춤 면접 질문을 받을 수 있습니다.")

    # 직무 선택
    resume_job = st.selectbox(
        "자소서 직무",
        JOB_FIELDS,
        key="resume_job_select",
    )

    # 기존 자소서 불러오기
    existing_resume = db.get_resume(resume_job)

    resume_text = st.text_area(
        "자기소개서 내용",
        value=existing_resume or "",
        height=400,
        placeholder="자기소개서 내용을 붙여넣기 해주세요...\n\n예시:\n[지원동기]\n저는 반도체 공정에 관심을 가지게 된 계기는...\n\n[성장과정]\n...\n\n[직무역량]\n...",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("저장", use_container_width=True, type="primary"):
            if resume_text and resume_text.strip():
                db.save_resume(resume_job, resume_text.strip())
                st.success(f"'{resume_job}' 직무 자소서가 저장되었습니다!")
            else:
                st.error("자소서 내용을 입력해주세요.")
    with col2:
        if st.button("홈으로", use_container_width=True):
            st.session_state["show_resume"] = False
            st.rerun()

    # 저장된 자소서 목록
    all_resumes = db.get_all_resumes()
    if all_resumes:
        st.markdown("---")
        st.markdown("**저장된 자소서 목록**")
        for r in all_resumes:
            with st.expander(f"[{r['job_field']}] 마지막 수정: {r['updated_at'][:10]}"):
                st.text(r['content'][:500] + ("..." if len(r['content']) > 500 else ""))


def render_feedback_form(db: InterviewDB):
    """사용자 피드백 수집 페이지."""
    st.subheader("💬 서비스 피드백")
    st.caption("Go터뷰를 사용해주셔서 감사합니다. 더 나은 서비스를 위해 의견을 남겨주세요!")

    with st.form("feedback_form"):
        rating = st.slider("만족도", 1, 5, 3, help="1: 매우 불만족 ~ 5: 매우 만족")

        st.markdown("⭐" * rating + "☆" * (5 - rating))

        comment = st.text_area(
            "사용 후기 / 개선 의견",
            placeholder="어떤 점이 좋았나요? 어떤 점이 아쉬웠나요?",
            height=100,
        )

        feature_request = st.text_area(
            "추가되었으면 하는 기능",
            placeholder="이런 기능이 있으면 좋겠어요...",
            height=80,
        )

        submitted = st.form_submit_button("피드백 제출", type="primary", use_container_width=True)
        if submitted:
            db.save_user_feedback(rating, comment, feature_request)
            st.success("피드백이 저장되었습니다! 소중한 의견 감사합니다. 🙏")

    # 기존 피드백 통계
    feedback_stats = db.get_feedback_stats()
    if feedback_stats["total_feedback"] > 0:
        st.markdown("---")
        st.markdown("**피드백 현황**")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("총 피드백 수", f"{feedback_stats['total_feedback']}건")
        with col2:
            avg = feedback_stats['avg_rating']
            st.metric("평균 만족도", f"{'⭐' * round(avg)} ({avg}/5)")

    if st.button("홈으로", use_container_width=True):
        st.session_state["show_feedback_form"] = False
        st.rerun()


def render_data_dashboard(db: InterviewDB):
    """데이터 대시보드 페이지."""
    st.subheader("📊 데이터 대시보드")
    st.caption("수집된 데이터 현황과 분석 결과를 확인하세요.")

    stats = db.get_stats()

    # 핵심 지표
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 면접 연습", f"{stats['total_interviews']}회")
    with col2:
        avg_score = stats['avg_score']
        st.metric("평균 점수", f"{avg_score}/100" if avg_score else "-")
    with col3:
        st.metric("질문 뱅크", f"{stats['question_bank_size']}개")
    with col4:
        feedback_stats = db.get_feedback_stats()
        st.metric("피드백 수", f"{feedback_stats['total_feedback']}건")

    st.markdown("---")

    # 직무별 분포
    if stats["job_distribution"]:
        st.markdown("**직무별 연습 현황**")
        for field, count in stats["job_distribution"].items():
            pct = count / stats["total_interviews"] if stats["total_interviews"] > 0 else 0
            st.progress(pct, text=f"{field}: {count}회 ({pct*100:.0f}%)")

    # 면접 유형별 분포
    st.markdown("---")
    st.markdown("**면접 유형별 현황**")
    records = db.get_all_records()
    type_counts = {}
    for r in records:
        t = r.get("interview_type", "직무면접")
        type_counts[t] = type_counts.get(t, 0) + 1
    if type_counts:
        for t, count in type_counts.items():
            st.write(f"- {t}: {count}회")
    else:
        st.info("아직 면접 기록이 없습니다.")

    # 점수 추이
    st.markdown("---")
    st.markdown("**최근 점수 추이**")
    scored_records = [r for r in records if r.get("score") is not None]
    if scored_records:
        # 최근 20개 (오래된 순)
        recent = list(reversed(scored_records[:20]))
        scores = [r["score"] for r in recent]
        st.line_chart({"점수": scores})
        if len(scores) >= 2:
            trend = scores[-1] - scores[0]
            if trend > 0:
                st.success(f"📈 점수가 {trend}점 상승했습니다! 꾸준히 성장하고 있어요.")
            elif trend < 0:
                st.warning(f"📉 점수가 {abs(trend)}점 하락했습니다. 다시 집중해봐요!")
            else:
                st.info("📊 점수가 유지되고 있습니다.")
    else:
        st.info("점수 데이터가 아직 없습니다. 면접 연습을 시작해보세요!")

    # 수집 데이터 요약
    st.markdown("---")
    st.markdown("**수집 데이터 요약**")
    all_resumes = db.get_all_resumes()
    st.markdown(f"""
| 데이터 항목 | 수량 | 활용 방안 |
|------------|------|----------|
| 면접 기록 | {stats['total_interviews']}건 | 답변 품질 추적, 성장 분석 |
| 질문 뱅크 | {stats['question_bank_size']}개 | 중복 방지, 질문 다양성 확보 |
| 자소서 | {len(all_resumes)}건 | 맞춤 질문 생성 |
| 사용자 피드백 | {feedback_stats['total_feedback']}건 | 서비스 개선 방향 도출 |
""")

    if st.button("홈으로", use_container_width=True):
        st.session_state["show_data_dashboard"] = False
        st.rerun()


def render_weakness_page(config: ConfigManager, db: InterviewDB):
    """🎯 약점 집중 연습 페이지.

    최근 면접 데이터에서 항목별 평균 점수를 시각화하고, 가장 취약한 영역에
    초점을 맞춘 맞춤 면접 질문을 생성한다.
    """
    st.subheader("🎯 약점 집중 연습")
    st.caption("최근 면접 평가 데이터에서 약점 영역을 식별해 집중적으로 강화할 수 있어요.")

    # 직무 필터
    filter_options = ["전체"] + JOB_FIELDS
    default_idx = 0
    prev = st.session_state.get("weakness_job_filter")
    if prev in filter_options:
        default_idx = filter_options.index(prev)
    selected = st.selectbox(
        "직무 필터",
        filter_options,
        index=default_idx,
        key="weakness_job_select",
    )
    st.session_state["weakness_job_filter"] = selected
    job_filter = None if selected == "전체" else selected

    profile = db.get_weakness_profile(job_field=job_filter)
    if not profile:
        st.info("최소 3건 이상의 평가 데이터가 필요합니다. 면접을 진행해 데이터를 모아주세요.")
        if st.button("홈으로", use_container_width=True):
            st.session_state["show_weakness_page"] = False
            st.rerun()
        return

    # 점수 분포 막대차트
    st.markdown("**📊 항목별 평균 점수 (최근 20건 기준 / 20점 만점)**")
    df = pd.DataFrame.from_dict(profile, orient="index", columns=["평균 점수"])
    st.bar_chart(df)

    # 가장 취약한 영역
    weakest = min(profile, key=profile.get)
    st.warning(f"가장 취약한 영역: **{weakest}** (평균 {profile[weakest]:.1f}점)")

    # 직무가 지정되지 않은 경우 약점 강화 질문은 어떤 직무로 만들지 안내
    target_job_for_question = job_filter or st.session_state.get("job_field") or JOB_FIELDS[0]
    target_bu = st.session_state.get("business_unit") or ""
    target_type = st.session_state.get("interview_type", "직무면접")
    st.caption(
        f"질문 생성 기준 → 직무: **{target_job_for_question}**"
        + (f", 사업부: **{target_bu}**" if target_bu else "")
        + f", 유형: **{target_type}**"
    )

    if st.button("🎯 이 약점을 강화하는 질문 받기", use_container_width=True, type="primary"):
        with st.spinner("약점 강화 질문을 생성하고 있습니다..."):
            try:
                ai_client = get_ai_client(config)
                resume_content = ""
                if target_type == "자소서기반면접":
                    resume_content = db.get_resume(target_job_for_question) or ""
                question = ai_client.generate_targeted_question(
                    job_field=target_job_for_question,
                    weakness=weakest,
                    interview_type=target_type,
                    business_unit=target_bu,
                    resume_content=resume_content,
                )
                # 약점 강화 모드로 정규 답변 플로우 진입
                st.session_state["weakness_target"] = weakest
                st.session_state["job_field"] = target_job_for_question
                st.session_state["business_unit"] = target_bu or None
                st.session_state["interview_type"] = target_type
                st.session_state["current_question"] = question
                st.session_state["feedback"] = None
                st.session_state["question_count"] = 0
                st.session_state["interview_active"] = True
                st.session_state["show_weakness_page"] = False
                st.rerun()
            except Exception as e:
                st.error(f"질문 생성 실패: {e}")

    if st.button("홈으로", use_container_width=True):
        st.session_state["show_weakness_page"] = False
        st.rerun()


def render_daily_quote():
    """오늘의 명언 렌더링 (API 호출 없이 하드코딩된 명언 사용)."""
    quote = get_daily_quote()
    st.markdown(
        f'<div class="quote-card"><p>"{quote}"</p></div>',
        unsafe_allow_html=True,
    )


def render_interview(config: ConfigManager, db: InterviewDB):
    job_field = st.session_state["job_field"]
    business_unit = st.session_state.get("business_unit")
    interview_type = st.session_state.get("interview_type", "직무면접")
    company = st.session_state.get("company", "")

    # 회사 정보 캐시 조회 (있으면 AI 프롬프트에 주입)
    company_info = db.get_company_info(company) if company else None

    type_emoji = {"직무면접": "💼", "인성면접": "🧠", "자소서기반면접": "📄"}
    job_label = f"{job_field}" + (f" ({business_unit})" if business_unit else "")
    header_text = f"{type_emoji.get(interview_type, '🎯')} {job_label} - {interview_type}"
    if company:
        header_text += f" / {company}"
        if company_info:
            header_text += " 📚"  # 캐시 적중 배지
    # 회사 인재상 배너 (선택한 회사가 캐시에 있을 때 면접 화면 맨 위에 표시)
    if company_info:
        talent_raw = (company_info.get('talent_profile') or '').strip()
        # 첫 문장만 추출 (마침표 기준), 없으면 앞 90자
        talent_summary = ""
        for sep in ['. ', '。', '.\n']:
            if sep in talent_raw:
                talent_summary = talent_raw.split(sep)[0].strip().rstrip('.') + '.'
                break
        if not talent_summary:
            talent_summary = (talent_raw[:90] + '…') if len(talent_raw) > 90 else talent_raw

        business_focus = (company_info.get('business_focus') or '').strip()
        # 주력 사업도 앞부분만
        if business_focus and ',' in business_focus:
            business_short = ' · '.join([s.strip() for s in business_focus.split(',')[:3]])
        else:
            business_short = business_focus[:80]

        industry = (company_info.get('industry') or '').strip()
        industry_html = f'<span class="cb-industry">{industry}</span>' if industry else ''
        focus_html = f'<div class="cb-focus">📌 주력: {business_short}</div>' if business_short else ''
        st.markdown(
            f'<div class="company-banner">'
            f'<div class="cb-name">🏢 {company_info["name"]} {industry_html}</div>'
            f'<div class="cb-talent">{talent_summary}</div>'
            f'{focus_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.subheader(header_text)
    st.caption(f"질문 #{st.session_state['question_count'] + 1}")

    if st.session_state["current_question"] is None:
        with st.spinner("질문을 준비하고 있습니다..."):
            try:
                ai_client = get_ai_client(config)

                # DB에서 과거 질문 컨텍스트 가져오기
                past_questions = db.get_past_questions_for_job(job_field, limit=5)
                common_questions = db.get_questions_for_job(job_field)

                # 컨텍스트를 포함한 질문 생성
                context_hint = ""
                if past_questions:
                    past_list = "\n".join(f"- {q}" for q in past_questions[:5])
                    context_hint += f"\n\n이전에 출제된 질문들 (중복 피해주세요):\n{past_list}"
                if common_questions:
                    sample = random.sample(common_questions, min(3, len(common_questions)))
                    common_list = "\n".join(f"- {q}" for q in sample)
                    context_hint += f"\n\n참고할 기출 질문 예시:\n{common_list}"

                # 자소서 기반이면 자소서 내용 가져오기
                resume_content = ""
                if interview_type == "자소서기반면접":
                    resume_content = db.get_resume(job_field) or ""

                question = ai_client.generate_question(
                    job_field,
                    context_hint=context_hint,
                    interview_type=interview_type,
                    resume_content=resume_content,
                    company=company,
                    business_unit=business_unit,
                    company_info=company_info,
                )
                st.session_state["current_question"] = question
                st.session_state["feedback"] = None
            except Exception as e:
                st.error(f"질문 생성 실패: {e}")
                return

    # 약점 강화 모드 배지
    if st.session_state.get("weakness_target"):
        st.caption(f"🎯 약점 강화 모드: {st.session_state['weakness_target']}")

    # 질문 표시
    st.markdown(
        f'<div class="question-box">{st.session_state["current_question"]}</div>',
        unsafe_allow_html=True,
    )

    if st.session_state["feedback"] is None:
        input_mode = st.radio(
            "답변 입력 방식",
            ["⌨️ 텍스트 입력", "🎤 음성 입력"],
            horizontal=True,
            key="answer_input_mode",
        )

        if input_mode == "🎤 음성 입력":
            from streamlit_mic_recorder import mic_recorder
            audio = mic_recorder(
                start_prompt="🎙️ 녹음 시작",
                stop_prompt="⏹️ 녹음 종료",
                just_once=True,
                use_container_width=True,
                format="wav",
                key="mic_input",
            )
            if audio and audio.get("bytes"):
                with st.spinner("음성을 텍스트로 변환 중..."):
                    try:
                        ai_client = get_ai_client(config)
                        transcribed = ai_client.transcribe_audio(audio["bytes"], mime_type="audio/wav")
                        st.session_state["transcribed_answer"] = transcribed
                        st.success("음성을 텍스트로 변환했습니다. 아래에서 확인 후 제출해주세요.")
                    except RuntimeError as e:
                        st.error(str(e))

        with st.form(key="answer_form"):
            user_answer = st.text_area(
                "답변을 입력하세요",
                value=st.session_state.get("transcribed_answer", ""),
                height=200,
                placeholder="면접 질문에 대한 답변을 작성해주세요...",
            )
            submitted = st.form_submit_button("답변 제출", type="primary", use_container_width=True)
            if submitted:
                if not user_answer or not user_answer.strip():
                    st.error("답변을 입력해주세요.")
                else:
                    with st.spinner("답변을 평가하고 있습니다..."):
                        try:
                            ai_client = get_ai_client(config)
                            feedback = ai_client.evaluate_answer(
                                st.session_state["current_question"],
                                user_answer.strip(),
                                job_field,
                                interview_type=interview_type,
                                company=company,
                                business_unit=business_unit,
                                company_info=company_info,
                            )
                            # 피드백에서 점수 추출
                            score = extract_score(feedback)
                            detail = parse_detail_scores(feedback)
                            st.session_state["feedback"] = feedback
                            st.session_state["last_answer"] = user_answer.strip()
                            st.session_state["question_count"] += 1
                            db.save_interview(
                                job_field=job_field,
                                question=st.session_state["current_question"],
                                answer=user_answer.strip(),
                                feedback=feedback,
                                score=score,
                                interview_type=interview_type,
                                business_unit=business_unit,
                                logic_score=detail.get("논리성"),
                                fit_score=detail.get("직무적합성"),
                                detail_score=detail.get("구체성"),
                                expression_score=detail.get("표현력"),
                                uniqueness_score=detail.get("차별성"),
                            )
                            st.session_state.pop("transcribed_answer", None)
                            # 약점 강화 모드는 답변 후 자동 해제
                            st.session_state.pop("weakness_target", None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"평가 실패: {e}")
    else:
        # 내 답변
        st.markdown("**내 답변**")
        st.markdown(st.session_state.get("last_answer", ""))

        # 점수 시각화
        feedback_text = st.session_state["feedback"]
        detail_scores = extract_detail_scores(feedback_text)
        total_score = extract_score(feedback_text)

        if detail_scores:
            st.markdown("---")
            st.markdown("**📊 항목별 점수**")
            score_cols = st.columns(5)
            score_labels = ["논리성", "직무적합성", "구체성", "표현력", "차별성"]
            for i, label in enumerate(score_labels):
                with score_cols[i]:
                    s = detail_scores.get(label, 0)
                    st.metric(label, f"{s}/20")

            if total_score is not None:
                st.markdown(f"### 총점: {total_score}/100점")

        # 피드백 카드
        st.markdown(
            f'<div class="feedback-card"><h4>AI 피드백</h4>{feedback_text}</div>',
            unsafe_allow_html=True,
        )

        # 동기부여 메시지
        motivation = random.choice(MOTIVATION_MESSAGES)
        st.markdown(
            f'<div class="motivation-msg">{motivation}</div>',
            unsafe_allow_html=True,
        )

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("다음 질문", use_container_width=True, type="primary"):
                st.session_state["current_question"] = None
                st.session_state["feedback"] = None
                st.rerun()
        with col2:
            if st.button("면접 종료", use_container_width=True):
                st.session_state["interview_active"] = False
                st.session_state["current_question"] = None
                st.session_state["feedback"] = None
                st.rerun()


def render_records(db: InterviewDB):
    st.subheader("면접 기록")

    # 통계 요약
    stats = db.get_stats()
    if stats["total_interviews"] > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                f'<div class="stats-card">'
                f'<div class="stat-number">{stats["total_interviews"]}</div>'
                f'<div class="stat-label">총 면접 횟수</div></div>',
                unsafe_allow_html=True,
            )
        with col2:
            avg_display = f'{stats["avg_score"]}점' if stats["avg_score"] else "-"
            st.markdown(
                f'<div class="stats-card">'
                f'<div class="stat-number">{avg_display}</div>'
                f'<div class="stat-label">평균 점수</div></div>',
                unsafe_allow_html=True,
            )
        with col3:
            field_display = stats["most_practiced_field"] or "-"
            st.markdown(
                f'<div class="stats-card">'
                f'<div class="stat-number">{field_display}</div>'
                f'<div class="stat-label">최다 연습 직무</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown("<br>", unsafe_allow_html=True)

        # 직무별 분포
        if stats["job_distribution"]:
            st.markdown("**직무별 연습 현황**")
            for field, count in stats["job_distribution"].items():
                st.progress(count / stats["total_interviews"], text=f"{field}: {count}회")

        st.markdown("---")

    # 기록 목록
    records = db.get_all_records()
    if not records:
        st.info("아직 저장된 면접 기록이 없습니다. 면접을 시작해보세요.")
        return

    job_fields_in_records = list(set(r["job_field"] for r in records))
    filter_job = st.selectbox("직무별 필터", ["전체"] + sorted(job_fields_in_records))
    if filter_job != "전체":
        records = [r for r in records if r["job_field"] == filter_job]

    st.caption(f"{len(records)}건의 기록")
    for record in records:
        interview_type = record.get('interview_type', '직무면접')
        type_emoji = {"직무면접": "💼", "인성면접": "🧠", "자소서기반면접": "📄"}
        emoji = type_emoji.get(interview_type, "🎯")
        bu = record.get('business_unit')
        job_label = f"[{record['job_field']}]" + (f"({bu})" if bu else "")
        with st.expander(f"{emoji} {job_label} {record['question'][:50]}... ({record['date'][:10]})"):
            st.markdown(f"**날짜:** {record['date']}")
            st.markdown(f"**직무:** {record['job_field']}" + (f" / **사업부:** {bu}" if bu else ""))
            st.markdown(f"**면접 유형:** {interview_type}")
            if record.get('score'):
                st.markdown(f"**점수:** {record['score']}/100")
            st.markdown(f"**질문:** {record['question']}")
            st.markdown("---")
            st.markdown("**내 답변:**")
            st.markdown(record['answer'])
            st.markdown("---")
            st.markdown("**AI 피드백:**")
            st.markdown(record['feedback'])


def render_home(config: ConfigManager, db: InterviewDB):
    # 오늘의 명언
    st.markdown("**오늘의 명언**")
    render_daily_quote()

    st.markdown("""
**Go터뷰**는 AI 면접관과 함께 실전 면접을 연습할 수 있는 서비스입니다.

**사용 방법:**
1. 사이드바에서 직무를 선택하세요
2. 면접 시작 버튼을 클릭하세요
3. AI가 생성한 질문에 답변을 작성하세요
4. AI가 논리성, 키워드, 개선점을 피드백해줍니다
5. 면접 기록은 자동으로 저장됩니다
""")

    # 간단한 통계 표시
    stats = db.get_stats()
    if stats["total_interviews"] > 0:
        st.markdown("---")
        st.markdown("**나의 연습 현황**")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("총 면접 연습", f"{stats['total_interviews']}회")
        with col2:
            if stats["most_practiced_field"]:
                st.metric("주력 직무", stats["most_practiced_field"])


def main():
    logo_uri = _logo_data_uri()
    st.set_page_config(
        page_title="Go터뷰",
        page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "🎯",
        layout="centered",
    )

    # 커스텀 CSS 적용
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    init_session_state()
    config = ConfigManager(st.session_state)
    db = InterviewDB()

    # 헤더 배너 (로고 + 워드마크 + 부제)
    logo_html = f'<img src="{logo_uri}" class="header-logo" alt="Go터뷰 로고" />' if logo_uri else ''
    st.markdown(
        f'<div class="header-banner">'
        f'{logo_html}'
        f'<div class="header-text">'
        f'<h1>Go터뷰</h1>'
        f'<p>AI 면접 연습 파트너</p>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    render_sidebar(config, db)

    if st.session_state.get("show_data_dashboard"):
        render_data_dashboard(db)
    elif st.session_state.get("show_feedback_form"):
        render_feedback_form(db)
    elif st.session_state.get("show_resume"):
        render_resume_page(db)
    elif st.session_state.get("show_records"):
        render_records(db)
    elif st.session_state.get("show_weakness_page"):
        render_weakness_page(config, db)
    elif st.session_state.get("interview_active"):
        render_interview(config, db)
    else:
        render_home(config, db)


if __name__ == "__main__":
    main()
