# -*- coding: utf-8 -*-
"""GoFactory 면접 연습 챗봇 메인 애플리케이션."""

import streamlit as st
import os

from ai_client import AIClient
from config import ConfigManager
from database import InterviewDB


JOB_FIELDS = ["반도체", "백엔드", "데이터", "마케팅", "기타 (직접 입력)"]


def get_ai_client(config: ConfigManager) -> AIClient:
    """Gemini + Groq 백업으로 AIClient 생성."""
    gemini_key = config.get_api_key()
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key:
        try:
            groq_key = st.secrets.get("GROQ_API_KEY", "")
        except Exception:
            groq_key = ""
    return AIClient(gemini_key=gemini_key, groq_key=groq_key)


def init_session_state():
    defaults = {
        "api_key": None,
        "current_question": None,
        "job_field": None,
        "interview_active": False,
        "feedback": None,
        "question_count": 0,
        "show_records": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar(config: ConfigManager, db: InterviewDB):
    with st.sidebar:
        st.header("🎯 면접 설정")

        if not config.is_configured():
            api_key_input = st.text_input(
                "Gemini API 키",
                type="password",
                placeholder="AIzaSy...",
            )
            if api_key_input and api_key_input.strip():
                config.set_api_key(api_key_input.strip())
                st.rerun()

        st.subheader("📋 직무 선택")
        selected_job = st.selectbox(
            "면접 직무를 선택하세요",
            JOB_FIELDS,
            index=0,
            label_visibility="collapsed",
        )

        if selected_job == "기타 (직접 입력)":
            custom_job = st.text_input("직무명 입력", placeholder="예: 프론트엔드, AI/ML...")
            if custom_job and custom_job.strip():
                selected_job = custom_job.strip()
            else:
                selected_job = None

        st.divider()
        if st.button("🚀 면접 시작", use_container_width=True, type="primary"):
            if not config.is_configured():
                st.error("API 키를 먼저 입력해주세요.")
            elif selected_job is None:
                st.error("직무명을 입력해주세요.")
            else:
                st.session_state["job_field"] = selected_job
                st.session_state["interview_active"] = True
                st.session_state["current_question"] = None
                st.session_state["feedback"] = None
                st.session_state["question_count"] = 0
                st.session_state["show_records"] = False
                st.rerun()

        if st.session_state.get("interview_active"):
            if st.button("⏹️ 면접 종료", use_container_width=True):
                st.session_state["interview_active"] = False
                st.session_state["current_question"] = None
                st.session_state["feedback"] = None
                st.rerun()

        st.divider()
        st.subheader("📚 면접 기록")
        record_count = db.get_record_count()
        st.caption(f"총 {record_count}개의 면접 기록")

        if st.button("📖 기록 보기", use_container_width=True):
            st.session_state["show_records"] = True
            st.session_state["interview_active"] = False
            st.rerun()

        if st.session_state.get("show_records"):
            if st.button("🔙 돌아가기", use_container_width=True):
                st.session_state["show_records"] = False
                st.rerun()


def render_daily_question(config: ConfigManager):
    st.subheader("💡 오늘의 면접 질문")
    if not config.is_configured():
        st.info("API 키를 설정하면 오늘의 질문을 확인할 수 있습니다.")
        return
    if "daily_question" not in st.session_state:
        try:
            ai_client = get_ai_client(config)
            st.session_state["daily_question"] = ai_client.generate_daily_question()
        except Exception:
            st.session_state["daily_question"] = "오늘의 질문을 불러오는 데 실패했습니다."
    st.info(f"**Q.** {st.session_state['daily_question']}")


def render_interview(config: ConfigManager, db: InterviewDB):
    job_field = st.session_state["job_field"]
    st.subheader(f"🎤 {job_field} 직무 면접 진행 중")
    st.caption(f"질문 #{st.session_state['question_count'] + 1}")

    if st.session_state["current_question"] is None:
        with st.spinner("면접 질문을 생성하고 있습니다..."):
            try:
                ai_client = get_ai_client(config)
                question = ai_client.generate_question(job_field)
                st.session_state["current_question"] = question
                st.session_state["feedback"] = None
            except Exception as e:
                st.error(f"질문 생성 실패: {e}")
                return

    st.markdown("---")
    st.markdown("### 📝 질문")
    st.markdown(f"> {st.session_state['current_question']}")
    st.markdown("---")

    if st.session_state["feedback"] is None:
        with st.form(key="answer_form"):
            user_answer = st.text_area(
                "답변을 입력하세요",
                height=200,
                placeholder="면접 질문에 대한 답변을 작성해주세요...",
            )
            submitted = st.form_submit_button("📤 답변 제출", type="primary", use_container_width=True)
            if submitted:
                if not user_answer or not user_answer.strip():
                    st.error("답변을 입력해주세요.")
                else:
                    with st.spinner("AI가 답변을 평가하고 있습니다..."):
                        try:
                            ai_client = get_ai_client(config)
                            feedback = ai_client.evaluate_answer(
                                st.session_state["current_question"],
                                user_answer.strip(),
                                job_field,
                            )
                            st.session_state["feedback"] = feedback
                            st.session_state["last_answer"] = user_answer.strip()
                            st.session_state["question_count"] += 1
                            db.save_interview(
                                job_field=job_field,
                                question=st.session_state["current_question"],
                                answer=user_answer.strip(),
                                feedback=feedback,
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"평가 실패: {e}")
    else:
        st.markdown("### 💬 내 답변")
        st.markdown(st.session_state.get("last_answer", ""))
        st.markdown("### 📊 AI 피드백")
        st.markdown(st.session_state["feedback"])
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➡️ 다음 질문", use_container_width=True, type="primary"):
                st.session_state["current_question"] = None
                st.session_state["feedback"] = None
                st.rerun()
        with col2:
            if st.button("⏹️ 면접 종료", use_container_width=True):
                st.session_state["interview_active"] = False
                st.session_state["current_question"] = None
                st.session_state["feedback"] = None
                st.rerun()


def render_records(db: InterviewDB):
    st.subheader("📚 면접 기록")
    records = db.get_all_records()
    if not records:
        st.info("아직 저장된 면접 기록이 없습니다. 면접을 시작해보세요!")
        return
    job_fields_in_records = list(set(r["job_field"] for r in records))
    filter_job = st.selectbox("직무별 필터", ["전체"] + sorted(job_fields_in_records))
    if filter_job != "전체":
        records = [r for r in records if r["job_field"] == filter_job]
    st.caption(f"총 {len(records)}개의 기록")
    for record in records:
        with st.expander(f"[{record['job_field']}] {record['question'][:50]}... ({record['date'][:10]})"):
            st.markdown(f"**날짜:** {record['date']}")
            st.markdown(f"**직무:** {record['job_field']}")
            st.markdown(f"**질문:** {record['question']}")
            st.markdown("---")
            st.markdown("**내 답변:**")
            st.markdown(record['answer'])
            st.markdown("---")
            st.markdown("**AI 피드백:**")
            st.markdown(record['feedback'])


def render_home(config: ConfigManager):
    st.markdown("""
### 👋 환영합니다!

**GoFactory 면접 연습**은 AI 면접관과 함께 실전 면접을 연습할 수 있는 서비스입니다.

#### 사용 방법:
1. 🎯 사이드바에서 **직무를 선택**하세요
2. 🚀 **면접 시작** 버튼을 클릭하세요
3. 📝 AI가 생성한 질문에 **답변을 작성**하세요
4. 📊 AI가 **논리성, 키워드, 개선점**을 피드백해줍니다
5. 📚 면접 기록은 자동으로 **저장**됩니다

---
""")
    render_daily_question(config)


def main():
    st.set_page_config(page_title="GoFactory 면접 연습", page_icon="🎯", layout="centered")
    init_session_state()
    config = ConfigManager(st.session_state)
    db = InterviewDB()
    st.title("🎯 GoFactory 면접 연습")
    st.caption("AI 면접관과 함께하는 실전 면접 연습 서비스")
    render_sidebar(config, db)
    if st.session_state.get("show_records"):
        render_records(db)
    elif st.session_state.get("interview_active"):
        render_interview(config, db)
    else:
        render_home(config)


if __name__ == "__main__":
    main()
