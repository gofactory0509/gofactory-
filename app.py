# -*- coding: utf-8 -*-
"""Go면접 챗봇 메인 애플리케이션."""

import streamlit as st
import os
import re
import random
from datetime import date

from ai_client import AIClient
from config import ConfigManager
from database import InterviewDB


JOB_FIELDS = ["반도체", "백엔드", "데이터", "마케팅", "기타 (직접 입력)"]
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
    /* 전체 배경 및 폰트 */
    .stApp {
        background: linear-gradient(180deg, #f8f9fc 0%, #ffffff 100%);
    }

    /* 헤더 배너 */
    .header-banner {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .header-banner h1 {
        margin: 0;
        font-size: 1.6rem;
        font-weight: 700;
        color: white;
    }
    .header-banner p {
        margin: 0.3rem 0 0 0;
        font-size: 0.9rem;
        opacity: 0.9;
        color: #e8e8ff;
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
        "interview_type": "직무면접",
        "interview_active": False,
        "feedback": None,
        "question_count": 0,
        "show_records": False,
        "show_resume": False,
        "show_feedback_form": False,
        "show_data_dashboard": False,
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


def render_sidebar(config: ConfigManager, db: InterviewDB):
    with st.sidebar:
        st.header("면접 설정")

        if not config.is_configured():
            api_key_input = st.text_input(
                "Gemini API 키",
                type="password",
                placeholder="AIzaSy...",
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
        )

        if selected_job == "기타 (직접 입력)":
            custom_job = st.text_input("직무명 입력", placeholder="예: 프론트엔드, AI/ML...")
            if custom_job and custom_job.strip():
                selected_job = custom_job.strip()
            else:
                selected_job = None

        # 면접 유형 선택
        st.subheader("면접 유형")
        selected_type = st.radio(
            "면접 유형을 선택하세요",
            INTERVIEW_TYPES,
            index=0,
            label_visibility="collapsed",
            help="자소서기반면접: 자소서를 먼저 등록해야 합니다",
        )

        st.divider()
        if st.button("면접 시작", use_container_width=True, type="primary"):
            if not config.is_configured():
                st.error("API 키를 먼저 입력해주세요.")
            elif selected_job is None:
                st.error("직무명을 입력해주세요.")
            elif selected_type == "자소서기반면접" and not db.get_resume(selected_job):
                st.error("자소서를 먼저 등록해주세요. 아래 '자소서 관리' 버튼을 눌러주세요.")
            else:
                st.session_state["job_field"] = selected_job
                st.session_state["interview_type"] = selected_type
                st.session_state["interview_active"] = True
                st.session_state["current_question"] = None
                st.session_state["feedback"] = None
                st.session_state["question_count"] = 0
                st.session_state["show_records"] = False
                st.session_state["show_resume"] = False
                st.session_state["show_feedback_form"] = False
                st.session_state["show_data_dashboard"] = False
                st.rerun()

        if st.session_state.get("interview_active"):
            if st.button("면접 종료", use_container_width=True):
                st.session_state["interview_active"] = False
                st.session_state["current_question"] = None
                st.session_state["feedback"] = None
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
                st.session_state["interview_active"] = False
                st.rerun()
        with col2:
            if st.button("📋 기록", use_container_width=True):
                st.session_state["show_records"] = True
                st.session_state["show_resume"] = False
                st.session_state["show_feedback_form"] = False
                st.session_state["show_data_dashboard"] = False
                st.session_state["interview_active"] = False
                st.rerun()

        col3, col4 = st.columns(2)
        with col3:
            if st.button("💬 피드백", use_container_width=True):
                st.session_state["show_feedback_form"] = True
                st.session_state["show_records"] = False
                st.session_state["show_resume"] = False
                st.session_state["show_data_dashboard"] = False
                st.session_state["interview_active"] = False
                st.rerun()
        with col4:
            if st.button("📊 대시보드", use_container_width=True):
                st.session_state["show_data_dashboard"] = True
                st.session_state["show_records"] = False
                st.session_state["show_resume"] = False
                st.session_state["show_feedback_form"] = False
                st.session_state["interview_active"] = False
                st.rerun()

        st.divider()
        record_count = db.get_record_count()
        st.caption(f"총 {record_count}건 면접 기록 저장됨")


def extract_score(feedback: str) -> int | None:
    """AI 피드백 텍스트에서 논리성 점수를 추출."""
    # "논리성 점수: 7/10" 또는 "논리성: 7/10" 패턴 매칭
    patterns = [
        r'논리성\s*점수\s*[:：]\s*(\d+)\s*/\s*10',
        r'논리성\s*[:：]\s*(\d+)\s*/\s*10',
        r'논리성.*?(\d+)\s*/\s*10',
        r'(\d+)\s*/\s*10\s*점',
    ]
    for pattern in patterns:
        match = re.search(pattern, feedback)
        if match:
            score = int(match.group(1))
            if 1 <= score <= 10:
                return score
    return None


def render_resume_page(db: InterviewDB):
    """자소서 관리 페이지."""
    st.subheader("📄 자소서 관리")
    st.caption("자소서를 등록하면 자소서 기반 맞춤 면접 질문을 받을 수 있습니다.")

    # 직무 선택
    resume_job = st.selectbox(
        "자소서 직무",
        [j for j in JOB_FIELDS if j != "기타 (직접 입력)"],
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
    st.caption("Go면접을 사용해주셔서 감사합니다. 더 나은 서비스를 위해 의견을 남겨주세요!")

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
        st.metric("평균 점수", f"{avg_score}/10" if avg_score else "-")
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


def render_daily_quote():
    """오늘의 명언 렌더링 (API 호출 없이 하드코딩된 명언 사용)."""
    quote = get_daily_quote()
    st.markdown(
        f'<div class="quote-card"><p>"{quote}"</p></div>',
        unsafe_allow_html=True,
    )


def render_interview(config: ConfigManager, db: InterviewDB):
    job_field = st.session_state["job_field"]
    interview_type = st.session_state.get("interview_type", "직무면접")

    type_emoji = {"직무면접": "💼", "인성면접": "🧠", "자소서기반면접": "📄"}
    st.subheader(f"{type_emoji.get(interview_type, '🎯')} {job_field} - {interview_type}")
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
                )
                st.session_state["current_question"] = question
                st.session_state["feedback"] = None
            except Exception as e:
                st.error(f"질문 생성 실패: {e}")
                return

    # 질문 표시
    st.markdown(
        f'<div class="question-box">{st.session_state["current_question"]}</div>',
        unsafe_allow_html=True,
    )

    if st.session_state["feedback"] is None:
        with st.form(key="answer_form"):
            user_answer = st.text_area(
                "답변을 입력하세요",
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
                            )
                            # 피드백에서 점수 추출
                            score = extract_score(feedback)
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
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"평가 실패: {e}")
    else:
        # 내 답변
        st.markdown("**내 답변**")
        st.markdown(st.session_state.get("last_answer", ""))

        # 피드백 카드
        st.markdown(
            f'<div class="feedback-card"><h4>AI 피드백</h4>{st.session_state["feedback"]}</div>',
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
        with st.expander(f"{emoji} [{record['job_field']}] {record['question'][:50]}... ({record['date'][:10]})"):
            st.markdown(f"**날짜:** {record['date']}")
            st.markdown(f"**직무:** {record['job_field']}")
            st.markdown(f"**면접 유형:** {interview_type}")
            if record.get('score'):
                st.markdown(f"**점수:** {record['score']}/10")
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
**Go면접**은 AI 면접관과 함께 실전 면접을 연습할 수 있는 서비스입니다.

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
    st.set_page_config(page_title="Go면접", page_icon="🎯", layout="centered")

    # 커스텀 CSS 적용
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    init_session_state()
    config = ConfigManager(st.session_state)
    db = InterviewDB()

    # 헤더 배너
    st.markdown(
        '<div class="header-banner">'
        '<h1>Go면접</h1>'
        '<p>AI 면접관과 함께하는 실전 면접 연습</p>'
        '</div>',
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
    elif st.session_state.get("interview_active"):
        render_interview(config, db)
    else:
        render_home(config, db)


if __name__ == "__main__":
    main()
