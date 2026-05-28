# -*- coding: utf-8 -*-
"""면접 기록 데이터베이스 모듈.

SQLite를 사용하여 면접 질문, 답변, 피드백을 저장하고 조회한다.
common_questions 테이블로 직무별 기출 질문을 관리한다.
"""

import sqlite3
from datetime import datetime


# 삼성전자 DS부문 '26상 공채 직무기술서 기준 10개 직무
# 출처: 삼성전자 DS부문 2026년 상반기 3급 신입사원 채용 직무기술서

JOB_DESCRIPTIONS = {
    "반도체공정기술": "반도체 8대 공정(Photo, Etch, Clean, CMP, Diffusion, IMP, Metal, CVD) 개발·고도화를 통해 생산성·수율·품질을 향상시키는 직무",
    "설비기술": "반도체 설비의 성능 향상·개조·개선과 Facility 지원을 통해 품질·수율·생산성을 향상시키는 직무",
    "회로설계": "시스템반도체(AP, Modem, Sensor, PMIC, DDI 등)의 Analog/Digital 회로 및 IP를 설계·검증하고 고객에게 솔루션을 제공하는 직무",
    "신호및시스템설계": "무선 통신 알고리즘(5G/6G/Wi-Fi), 영상 처리 알고리즘(ISP, CV) 또는 IT 인프라·보안 아키텍처를 설계·연구하는 직무",
    "평가및분석": "반도체 제품의 특성 평가·분석 Test Program 개발, 설계·공정 불량 검출, 신뢰성·품질 보증을 담당하는 직무",
    "반도체공정설계": "반도체 공정 아키텍처 설계, 소자 개발, Process Integration, 수율 향상 및 패키지 설계·Simulation을 담당하는 직무",
    "생산관리": "생산 기획, 생산성 관리, SCM, 시스템 기반 생산체계 구축을 통해 생산성을 극대화하는 직무",
    "인프라기술": "반도체 생산 인프라 건설·기획, Facility/Utility(HVAC, UPW, Bulk Gas 등) 운영, 전력 계통 운영을 담당하는 직무",
    "환경": "통합환경관리, 자원 순환, 친환경 인증(ISO/RBA/ZWTL) 등 반도체 공정 환경 법규 준수 및 ESG 관련 업무를 수행하는 직무",
    "SW개발": "AI/SW 기술을 바탕으로 반도체 도메인 특화 AI 모델·Agent·Platform을 개발하여 Autonomous Fab을 구현하는 직무",
}

# 직무가 모집되는 사업부 매핑 (삼성전자 DS부문 '26상 공채 기준)
JOB_BUSINESS_UNITS = {
    "반도체공정기술": ["메모리", "Foundry", "반도체연구소", "TSP총괄"],
    "설비기술": ["메모리", "Foundry", "반도체연구소"],
    "회로설계": ["S.LSI", "Foundry"],
    "신호및시스템설계": ["S.LSI", "AI센터"],
    "평가및분석": ["S.LSI", "Foundry"],
    "반도체공정설계": ["S.LSI", "Foundry"],
    "생산관리": ["Foundry", "TSP총괄"],
    "인프라기술": ["글로벌 제조&인프라"],
    "환경": ["글로벌 제조&인프라"],
    "SW개발": ["AI센터"],
}

# 직무별 사전 등록 면접 질문 (직무기술서 Role / Requirements 기반)
SEED_QUESTIONS = {
    "반도체공정기술": [
        ("반도체 8대 공정(Photo, Etch, Clean, CMP, Diffusion, IMP, Metal, CVD)을 간단히 설명해주세요.", "하"),
        ("Defect(불량) 발생 원인을 규명할 때 사용하는 분석 방법론을 설명해주세요.", "중"),
        ("CVD와 PVD의 차이점, 그리고 각 공정의 장단점을 설명해주세요.", "중"),
        ("반도체 수율(Yield)을 결정짓는 주요 요인과 향상 방법을 설명해주세요.", "중"),
        ("계측(Metrology) 공정에서 측정 결과의 신뢰성을 향상시키는 방법은 무엇인가요?", "중"),
        ("EUV 리소그래피가 미세공정에 도입된 이유와 기술적 난제를 설명해주세요.", "상"),
        ("빅데이터 분석을 활용해 공정 자동화 시스템을 구축한다면 어떤 데이터를 수집하고 어떤 모델을 적용하시겠어요?", "상"),
    ],
    "설비기술": [
        ("PM(Preventive Maintenance)과 BM(Break Maintenance)의 차이를 설명해주세요.", "하"),
        ("반도체 설비에서 플라즈마, 진공, 가스 제어가 중요한 이유를 설명해주세요.", "중"),
        ("설비 가동률을 향상시키기 위한 방법론을 제시해주세요.", "중"),
        ("열전달, 진공, 유체역학 중 하나를 골라 반도체 설비에서의 활용 예시를 설명해주세요.", "중"),
        ("IoT 센서를 활용한 Smart Factory 구축 시 고려해야 할 점을 설명해주세요.", "중"),
        ("신설비 셋업 시 어떤 기준으로 최적 조건을 결정하시겠어요?", "상"),
        ("설비 고장 데이터를 분석해 예방 정비 시점을 예측하는 방법을 설명해주세요.", "상"),
    ],
    "회로설계": [
        ("Analog와 Digital 회로 설계의 핵심 차이점을 설명해주세요.", "하"),
        ("Verilog로 작성한 RTL이 실제 하드웨어로 합성되는 과정을 설명해주세요.", "중"),
        ("PLL(Phase-Locked Loop)의 동작 원리와 주요 설계 고려사항을 설명해주세요.", "중"),
        ("PPA(Power, Performance, Area) 최적화를 위한 설계 전략을 설명해주세요.", "중"),
        ("SRAM Bit-cell 설계 시 안정성과 면적 사이의 트레이드오프를 설명해주세요.", "중"),
        ("AI NPU 설계 시 일반 SoC 설계와 다르게 고려해야 할 점은 무엇인가요?", "상"),
        ("고속 SerDes 설계에서 Signal Integrity 이슈를 해결하는 방법을 설명해주세요.", "상"),
    ],
    "신호및시스템설계": [
        ("5G 통신과 4G LTE의 핵심 차이점을 설명해주세요.", "하"),
        ("Channel Estimation의 목적과 일반적인 알고리즘을 설명해주세요.", "중"),
        ("ISP(Image Signal Processor)에서 Demosaicing 알고리즘의 역할은 무엇인가요?", "중"),
        ("FFT(Fast Fourier Transform)가 통신 시스템에서 사용되는 이유를 설명해주세요.", "중"),
        ("Beamforming의 원리와 5G에서의 활용을 설명해주세요.", "중"),
        ("6G에서 새롭게 등장하는 기술 트렌드와 도전 과제를 설명해주세요.", "상"),
        ("Deep Learning 기반 Image Super-Resolution을 모바일 ISP에 적용할 때 고려사항은?", "상"),
    ],
    "평가및분석": [
        ("ATE(Automated Test Equipment)의 역할을 설명해주세요.", "하"),
        ("전기적 불량 분석(EFA)과 물리적 불량 분석(PFA)의 차이를 설명해주세요.", "중"),
        ("반도체 신뢰성 평가 항목 중 HTOL과 TC를 설명해주세요.", "중"),
        ("Process/Voltage/Temperature(PVT) 변동에 따른 회로 동작 검증 방법은?", "중"),
        ("Probe Card의 역할과 양산 품질 관리 방법을 설명해주세요.", "중"),
        ("Test Cost를 줄이면서 Test Coverage를 유지하는 전략을 설명해주세요.", "상"),
        ("AI를 활용해 수율 데이터에서 불량 패턴을 자동 검출하는 시스템을 설계한다면?", "상"),
    ],
    "반도체공정설계": [
        ("Process Integration이 무엇인지 설명해주세요.", "하"),
        ("MOSFET의 동작 원리와 주요 설계 파라미터를 설명해주세요.", "중"),
        ("FinFET과 GAA(Gate-All-Around) 트랜지스터의 구조적 차이와 장점을 설명해주세요.", "중"),
        ("DTCO(Design Technology Co-Optimization)의 개념과 필요성을 설명해주세요.", "중"),
        ("TCAD Simulation을 활용한 소자 설계 워크플로우를 설명해주세요.", "중"),
        ("EUV 기반 3nm 이하 공정 개발 시 주요 도전 과제는 무엇인가요?", "상"),
        ("HBM(High Bandwidth Memory) Base Die 공정 개발 시 고려사항을 설명해주세요.", "상"),
    ],
    "생산관리": [
        ("SCM(Supply Chain Management)의 핵심 구성 요소를 설명해주세요.", "하"),
        ("반도체 생산에서 Bottleneck 공정을 식별하고 개선하는 방법은?", "중"),
        ("생산 계획 수립 시 자재 리드타임과 수율 변동성을 어떻게 반영하시겠어요?", "중"),
        ("Wafer Cost 변동 요인과 원가 절감 방안을 설명해주세요.", "중"),
        ("통계적 공정 관리(SPC)의 핵심 지표를 설명해주세요.", "중"),
        ("시스템 시뮬레이션을 활용해 생산성 향상을 입증하는 방법론을 설명해주세요.", "상"),
        ("Global OSAT 운영 시 SCM 측면에서 고려해야 할 리스크는?", "상"),
    ],
    "인프라기술": [
        ("반도체 FAB에서 클린룸이 필요한 이유와 등급(Class) 기준을 설명해주세요.", "하"),
        ("HVAC 시스템이 반도체 공정에 미치는 영향을 설명해주세요.", "중"),
        ("UPW(Ultra Pure Water)의 품질 기준과 생산 방식을 설명해주세요.", "중"),
        ("무정전 전원 공급(UPS)을 위한 전력 계통 운영 방안을 설명해주세요.", "중"),
        ("Bulk Gas 공급 시스템 운영 시 안전 관리 포인트는 무엇인가요?", "중"),
        ("신규 FAB 건설 시 마스터 스케줄을 어떻게 수립하시겠어요?", "상"),
        ("BIM(Building Information Modeling)을 FAB 설계에 적용했을 때의 이점은?", "상"),
    ],
    "환경": [
        ("ESG의 의미와 반도체 산업에서 중요한 이유를 설명해주세요.", "하"),
        ("통합환경관리법의 핵심 내용을 설명해주세요.", "중"),
        ("반도체 공정에서 발생하는 주요 폐기물과 처리 방법을 설명해주세요.", "중"),
        ("ZWTL(Zero Waste to Landfill) 인증을 받기 위한 조건을 설명해주세요.", "중"),
        ("환경 안전사고 예방을 위해 어떤 리스크 평가 방법론을 적용하시겠어요?", "중"),
        ("RE100과 반도체 기업이 달성해야 할 과제를 설명해주세요.", "상"),
        ("반도체 공정의 PFC(과불화화합물) 배출을 줄이기 위한 방안은?", "상"),
    ],
    "SW개발": [
        ("Python과 C++의 주요 차이점, 그리고 AI 모델 개발에 Python을 많이 쓰는 이유를 설명해주세요.", "하"),
        ("LLM(Large Language Model)의 기본 구조와 학습 방식을 설명해주세요.", "중"),
        ("RAG(Retrieval-Augmented Generation)의 동작 원리와 활용 사례를 설명해주세요.", "중"),
        ("MLOps와 DevOps의 차이를 설명해주세요.", "중"),
        ("LLM 추론 비용을 최적화하는 방법(Quantization, Distillation, Caching 등) 중 하나를 설명해주세요.", "중"),
        ("반도체 공정 데이터로 이상 감지 AI 모델을 만든다면 어떤 알고리즘과 데이터 전처리를 적용하시겠어요?", "상"),
        ("Digital Twin을 활용한 Autonomous Fab을 구현할 때 핵심 기술 스택은?", "상"),
    ],
}


# 회사 정보 수동 시드 (Phase 1 PoC — Phase 2부터 AWS Batch로 자동 갱신)
# 각 회사의 인재상·주력사업·최근 트렌드는 LLM 학습 데이터 기반 작성
# Phase 2에서 네이버 뉴스 API + DART + 채용 페이지 크롤링으로 자동 갱신 예정
COMPANY_SEEDS = [
    {
        "name": "삼성전자",
        "aliases": "삼성, Samsung, SEC, 삼성반도체, Samsung Electronics, Samsung DS",
        "industry": "반도체-IDM (메모리·시스템·Foundry)",
        "talent_profile": (
            "도전 의식과 창의력으로 변화를 선도하는 인재. "
            "'Inspire the World, Create the Future' 비전 아래 전문성·협업·글로벌 감각을 중시. "
            "DS부문은 반도체 8대 공정에 대한 깊은 이해와 빅데이터 분석 역량을 강조."
        ),
        "business_focus": (
            "DRAM, NAND, HBM, Foundry(EUV 3nm GAA), AI 반도체(NPU), "
            "시스템반도체(Exynos, ISOCELL Image Sensor, DDI, PMIC)"
        ),
        "recent_news_summary": (
            "2026년 HBM4 양산 본격화, AI 반도체 'Mach-1' 발표, Foundry 사업 확장. "
            "3nm GAA 공정 안정화 후 2nm 양산 준비. NVIDIA·구글 등 AI 가속기 시장 진입 가속화."
        ),
        "recruiting_status": "2026 상반기 3급 신입 약 1,000명 규모 (공정기술/설비기술/회로설계/평가및분석/SW개발 등)",
        "source_urls": "https://www.samsung-dsrecruit.com/",
    },
    {
        "name": "SK하이닉스",
        "aliases": "SK Hynix, 하이닉스, Hynix, SKHynix",
        "industry": "반도체-IDM (메모리)",
        "talent_profile": (
            "SUPEX(Super Excellent) 수준의 도전 정신, 자율과 책임. "
            "'세상의 모든 것을 가능케 하는 ICT 솔루션' 비전. "
            "끊임없는 혁신·글로벌 마인드·협업 능력 중시."
        ),
        "business_focus": "DRAM, NAND, HBM(글로벌 1위), CXL, AI 메모리(GDDR7)",
        "recent_news_summary": (
            "2026년 HBM3E 12단 양산, NVIDIA Blackwell·Rubin 주력 공급사 지위. "
            "HBM4 개발 가속, 청주 M15X·용인 클러스터 증설로 HBM 캐파 대폭 확대."
        ),
        "recruiting_status": "HBM 호황으로 채용 확대, 메모리 설계·공정 직무 강세",
        "source_urls": "https://recruit.skhynix.com/",
    },
    {
        "name": "DB하이텍",
        "aliases": "DB하이텍, DB HiTek, 동부하이텍",
        "industry": "반도체-Foundry (8인치 특화)",
        "talent_profile": (
            "도전·변화·혁신을 추구하며 고객 중심 사고 중시. "
            "8인치 파운드리 전문성과 다품종 소량 생산 대응 능력을 가진 인재 선호."
        ),
        "business_focus": (
            "8인치 파운드리: BCDMOS 전력반도체, CMOS Image Sensor, DDI(Display Driver IC), "
            "MEMS, 차량용 반도체"
        ),
        "recent_news_summary": (
            "전력반도체 호황으로 가동률 100% 유지. 12인치 파운드리 진출 검토 중. "
            "차량용 IGBT·SiC 등 전동화 수요 확대 대응, GaN 화합물 반도체 진출."
        ),
        "recruiting_status": "공정 엔지니어·설비기술 중심 채용",
        "source_urls": "https://www.dbhitek.com/",
    },
    {
        "name": "한미반도체",
        "aliases": "한미반도체, HANMI Semiconductor, Hanmi",
        "industry": "반도체-장비 (HBM 후공정)",
        "talent_profile": (
            "도전·글로벌·끊임없는 혁신. 'Vision 2030 - World No.1 Equipment Maker' 목표. "
            "기술 전문성과 글로벌 협업 능력을 갖춘 인재 선호."
        ),
        "business_focus": "HBM TC Bonder(열압착 본더), Dual TC Bonder, Vision Placement(검사 장비)",
        "recent_news_summary": (
            "SK하이닉스·마이크론 HBM TC Bonder 핵심 공급사. "
            "2025-2026년 매출 사상 최대 갱신. 듀얼 TC 본더 신제품 출시로 HBM4 시대 대응."
        ),
        "recruiting_status": "HBM 시장 폭증으로 R&D·생산 채용 급증",
        "source_urls": "https://www.hanmisemi.com/",
    },
    {
        "name": "솔브레인",
        "aliases": "솔브레인, Soulbrain",
        "industry": "반도체-소재 (화학 소재)",
        "talent_profile": (
            "도전과 협력을 통해 화학 혁신을 만드는 인재. "
            "끊임없는 R&D 투자, 고객사와의 긴밀한 협업, 자기 주도적 문제 해결 능력 중시."
        ),
        "business_focus": (
            "반도체 화학 소재: 식각액(BOE/HF), CMP 슬러리, 전구체(Precursor), 박막 소재. "
            "2차전지 전해액 사업도 확장 중."
        ),
        "recent_news_summary": (
            "HBM·EUV용 신소재 매출 확대. 일본 의존도 낮추는 국산화 핵심 기업. "
            "2차전지 전해액 시장 진입으로 사업 다각화."
        ),
        "recruiting_status": "화학·재료 전공 R&D 채용 강세",
        "source_urls": "https://www.soulbrain.co.kr/",
    },
]


class InterviewDB:
    """면접 기록 SQLite 데이터베이스.

    면접 세션의 질문, 답변, 피드백을 저장하고 조회하는 기능을 제공한다.
    직무별 기출 질문 관리 및 통계 기능을 포함한다.
    자소서 저장 및 사용자 피드백 수집 기능을 포함한다.
    """

    def __init__(self, db_path: str = "interviews.db"):
        """데이터베이스 연결 및 테이블 생성.

        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._seed_common_questions()
        self._seed_companies()

    def _create_tables(self):
        """면접 기록, 질문 뱅크, 자소서, 피드백 테이블 생성."""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS interviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                job_field TEXT NOT NULL,
                interview_type TEXT DEFAULT '직무면접',
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                feedback TEXT NOT NULL,
                score INTEGER,
                logic_score INTEGER,
                fit_score INTEGER,
                detail_score INTEGER,
                expression_score INTEGER,
                uniqueness_score INTEGER
            )
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS common_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_field TEXT NOT NULL,
                question TEXT NOT NULL,
                difficulty TEXT DEFAULT '중'
            )
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS question_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_field TEXT NOT NULL,
                question TEXT NOT NULL,
                source TEXT DEFAULT 'ai_generated',
                created_at TEXT NOT NULL
            )
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_field TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT,
                feature_request TEXT
            )
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                aliases TEXT,
                industry TEXT,
                talent_profile TEXT,
                business_focus TEXT,
                recent_news_summary TEXT,
                recruiting_status TEXT,
                source_urls TEXT,
                last_updated TEXT NOT NULL,
                is_cached INTEGER DEFAULT 1
            )
        ''')
        # 기존 DB 호환을 위한 컬럼 마이그레이션
        for ddl in (
            'ALTER TABLE interviews ADD COLUMN interview_type TEXT DEFAULT "직무면접"',
            'ALTER TABLE interviews ADD COLUMN business_unit TEXT',
            'ALTER TABLE interviews ADD COLUMN logic_score INTEGER',
            'ALTER TABLE interviews ADD COLUMN fit_score INTEGER',
            'ALTER TABLE interviews ADD COLUMN detail_score INTEGER',
            'ALTER TABLE interviews ADD COLUMN expression_score INTEGER',
            'ALTER TABLE interviews ADD COLUMN uniqueness_score INTEGER',
        ):
            try:
                self.conn.execute(ddl)
            except sqlite3.OperationalError:
                pass
        self.conn.commit()

    def _seed_common_questions(self):
        """사전 등록 질문 시드. 새 직무 카탈로그 시드가 없으면 기존 시드를 비우고 재삽입."""
        new_jobs = list(SEED_QUESTIONS.keys())
        placeholders = ",".join(["?"] * len(new_jobs))
        cursor = self.conn.execute(
            f'SELECT COUNT(*) FROM common_questions WHERE job_field IN ({placeholders})',
            new_jobs,
        )
        if cursor.fetchone()[0] > 0:
            return

        self.conn.execute('DELETE FROM common_questions')
        for job_field, questions in SEED_QUESTIONS.items():
            for question_text, difficulty in questions:
                self.conn.execute(
                    'INSERT INTO common_questions (job_field, question, difficulty) VALUES (?, ?, ?)',
                    (job_field, question_text, difficulty)
                )
        self.conn.commit()

    def save_interview(
        self,
        job_field: str,
        question: str,
        answer: str,
        feedback: str,
        score: int | None = None,
        interview_type: str = "직무면접",
        business_unit: str | None = None,
        logic_score: int | None = None,
        fit_score: int | None = None,
        detail_score: int | None = None,
        expression_score: int | None = None,
        uniqueness_score: int | None = None,
    ):
        """면접 기록 저장.

        Args:
            job_field: 직무 분야
            question: 면접 질문
            answer: 사용자 답변
            feedback: AI 피드백
            score: 총점 (선택)
            interview_type: 면접 유형 (직무면접/인성면접/자소서기반면접)
            business_unit: 사업부 (메모리/Foundry/S.LSI 등, 선택)
            logic_score: 논리성 점수 (0~20, 선택)
            fit_score: 직무적합성 점수 (0~20, 선택)
            detail_score: 구체성 점수 (0~20, 선택)
            expression_score: 표현력 점수 (0~20, 선택)
            uniqueness_score: 차별성 점수 (0~20, 선택)
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute(
            '''INSERT INTO interviews (
                   date, job_field, interview_type, business_unit, question, answer, feedback, score,
                   logic_score, fit_score, detail_score, expression_score, uniqueness_score
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                now, job_field, interview_type, business_unit, question, answer, feedback, score,
                logic_score, fit_score, detail_score, expression_score, uniqueness_score,
            )
        )
        self.conn.commit()

        # 질문을 question_bank에도 추가
        self._add_to_question_bank(job_field, question)

    def _add_to_question_bank(self, job_field: str, question: str):
        """AI가 생성한 질문을 질문 뱅크에 저장 (중복 방지)."""
        cursor = self.conn.execute(
            'SELECT COUNT(*) FROM question_bank WHERE question = ?',
            (question,)
        )
        if cursor.fetchone()[0] == 0:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.conn.execute(
                'INSERT INTO question_bank (job_field, question, source, created_at) VALUES (?, ?, ?, ?)',
                (job_field, question, 'ai_generated', now)
            )
            self.conn.commit()

    def get_questions_for_job(self, job_field: str) -> list[str]:
        """직무별 사전 등록 질문 목록 반환.

        Args:
            job_field: 직무 분야

        Returns:
            list[str]: 해당 직무의 질문 리스트
        """
        cursor = self.conn.execute(
            'SELECT question FROM common_questions WHERE job_field = ?',
            (job_field,)
        )
        return [row[0] for row in cursor.fetchall()]

    def get_past_questions_for_job(self, job_field: str, limit: int = 10) -> list[str]:
        """직무별 과거 출제 질문 반환 (question_bank + interviews).

        Args:
            job_field: 직무 분야
            limit: 최대 반환 개수

        Returns:
            list[str]: 과거 질문 리스트
        """
        cursor = self.conn.execute(
            'SELECT DISTINCT question FROM question_bank WHERE job_field = ? ORDER BY created_at DESC LIMIT ?',
            (job_field, limit)
        )
        return [row[0] for row in cursor.fetchall()]

    def get_all_records(self) -> list[dict]:
        """모든 면접 기록 조회 (최신순).

        Returns:
            list[dict]: 면접 기록 리스트
        """
        cursor = self.conn.execute(
            'SELECT * FROM interviews ORDER BY date DESC'
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_records_by_job(self, job_field: str) -> list[dict]:
        """직무별 면접 기록 조회.

        Args:
            job_field: 직무 분야

        Returns:
            list[dict]: 해당 직무의 면접 기록 리스트
        """
        cursor = self.conn.execute(
            'SELECT * FROM interviews WHERE job_field = ? ORDER BY date DESC',
            (job_field,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_record_count(self) -> int:
        """총 면접 기록 수 반환.

        Returns:
            int: 저장된 면접 기록 수
        """
        cursor = self.conn.execute('SELECT COUNT(*) FROM interviews')
        return cursor.fetchone()[0]

    def get_stats(self) -> dict:
        """면접 통계 반환.

        Returns:
            dict: total_interviews, avg_score, most_practiced_field, job_distribution
        """
        stats = {}

        # 총 면접 횟수
        cursor = self.conn.execute('SELECT COUNT(*) FROM interviews')
        stats["total_interviews"] = cursor.fetchone()[0]

        # 평균 점수 (score가 있는 경우만)
        cursor = self.conn.execute('SELECT AVG(score) FROM interviews WHERE score IS NOT NULL')
        avg = cursor.fetchone()[0]
        stats["avg_score"] = round(avg, 1) if avg else None

        # 직무별 분포
        cursor = self.conn.execute(
            'SELECT job_field, COUNT(*) as cnt FROM interviews GROUP BY job_field ORDER BY cnt DESC'
        )
        distribution = {}
        for row in cursor.fetchall():
            distribution[row[0]] = row[1]
        stats["job_distribution"] = distribution

        # 가장 많이 연습한 직무
        if distribution:
            stats["most_practiced_field"] = max(distribution, key=distribution.get)
        else:
            stats["most_practiced_field"] = None

        # question_bank 크기
        cursor = self.conn.execute('SELECT COUNT(*) FROM question_bank')
        stats["question_bank_size"] = cursor.fetchone()[0]

        return stats

    def get_weakness_profile(self, job_field: str | None = None, limit: int = 20) -> dict:
        """최근 N건 면접 평가의 항목별 평균 점수 (NULL 제외).

        Args:
            job_field: 직무 분야 (선택, 미지정 시 전체)
            limit: 최근 N건 (기본 20)

        Returns:
            dict: {'논리성': float, '직무적합성': float, '구체성': float, '표현력': float, '차별성': float}
                  점수 데이터가 3건 미만이면 빈 dict 반환.
                  값이 NULL인 항목은 키 자체가 빠짐.
        """
        # 점수가 하나라도 있는 행만 카운트
        if job_field:
            cursor = self.conn.execute(
                '''SELECT COUNT(*) FROM interviews
                   WHERE job_field = ?
                     AND (logic_score IS NOT NULL OR fit_score IS NOT NULL
                          OR detail_score IS NOT NULL OR expression_score IS NOT NULL
                          OR uniqueness_score IS NOT NULL)''',
                (job_field,),
            )
        else:
            cursor = self.conn.execute(
                '''SELECT COUNT(*) FROM interviews
                   WHERE (logic_score IS NOT NULL OR fit_score IS NOT NULL
                          OR detail_score IS NOT NULL OR expression_score IS NOT NULL
                          OR uniqueness_score IS NOT NULL)''',
            )
        scored_count = cursor.fetchone()[0]
        if scored_count < 3:
            return {}

        # 최근 N건의 평균 계산 (NULL은 AVG에서 자동 제외)
        if job_field:
            cursor = self.conn.execute(
                '''SELECT AVG(logic_score), AVG(fit_score), AVG(detail_score),
                          AVG(expression_score), AVG(uniqueness_score)
                   FROM (
                       SELECT logic_score, fit_score, detail_score, expression_score, uniqueness_score
                       FROM interviews
                       WHERE job_field = ?
                       ORDER BY date DESC
                       LIMIT ?
                   )''',
                (job_field, limit),
            )
        else:
            cursor = self.conn.execute(
                '''SELECT AVG(logic_score), AVG(fit_score), AVG(detail_score),
                          AVG(expression_score), AVG(uniqueness_score)
                   FROM (
                       SELECT logic_score, fit_score, detail_score, expression_score, uniqueness_score
                       FROM interviews
                       ORDER BY date DESC
                       LIMIT ?
                   )''',
                (limit,),
            )
        row = cursor.fetchone()
        labels = ["논리성", "직무적합성", "구체성", "표현력", "차별성"]
        profile: dict = {}
        for label, value in zip(labels, row):
            if value is not None:
                profile[label] = float(value)
        return profile

    def close(self):
        """데이터베이스 연결 종료."""
        self.conn.close()

    # ─── 자소서 관련 메서드 ───

    def save_resume(self, job_field: str, content: str) -> int:
        """자소서 저장 (같은 직무면 업데이트).

        Args:
            job_field: 직무 분야
            content: 자소서 내용

        Returns:
            int: 저장된 레코드 ID
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 같은 직무의 기존 자소서가 있으면 업데이트
        cursor = self.conn.execute(
            'SELECT id FROM resumes WHERE job_field = ?', (job_field,)
        )
        existing = cursor.fetchone()
        if existing:
            self.conn.execute(
                'UPDATE resumes SET content = ?, updated_at = ? WHERE id = ?',
                (content, now, existing[0])
            )
            self.conn.commit()
            return existing[0]
        else:
            cursor = self.conn.execute(
                'INSERT INTO resumes (job_field, content, created_at, updated_at) VALUES (?, ?, ?, ?)',
                (job_field, content, now, now)
            )
            self.conn.commit()
            return cursor.lastrowid

    def get_resume(self, job_field: str) -> str | None:
        """직무별 자소서 조회.

        Args:
            job_field: 직무 분야

        Returns:
            str | None: 자소서 내용 또는 None
        """
        cursor = self.conn.execute(
            'SELECT content FROM resumes WHERE job_field = ? ORDER BY updated_at DESC LIMIT 1',
            (job_field,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def get_all_resumes(self) -> list[dict]:
        """모든 자소서 조회.

        Returns:
            list[dict]: 자소서 리스트
        """
        cursor = self.conn.execute('SELECT * FROM resumes ORDER BY updated_at DESC')
        return [dict(row) for row in cursor.fetchall()]

    # ─── 사용자 피드백 관련 메서드 ───

    def save_user_feedback(self, rating: int, comment: str = "", feature_request: str = ""):
        """사용자 피드백 저장.

        Args:
            rating: 만족도 (1~5)
            comment: 자유 의견
            feature_request: 기능 요청
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute(
            'INSERT INTO user_feedback (date, rating, comment, feature_request) VALUES (?, ?, ?, ?)',
            (now, rating, comment, feature_request)
        )
        self.conn.commit()

    def get_all_feedback(self) -> list[dict]:
        """모든 사용자 피드백 조회.

        Returns:
            list[dict]: 피드백 리스트
        """
        cursor = self.conn.execute('SELECT * FROM user_feedback ORDER BY date DESC')
        return [dict(row) for row in cursor.fetchall()]

    def get_feedback_stats(self) -> dict:
        """피드백 통계 반환.

        Returns:
            dict: 총 피드백 수, 평균 만족도
        """
        cursor = self.conn.execute('SELECT COUNT(*), AVG(rating) FROM user_feedback')
        row = cursor.fetchone()
        return {
            "total_feedback": row[0] or 0,
            "avg_rating": round(row[1], 1) if row[1] else None,
        }

    # ─── 회사 정보 캐시 관련 메서드 ───

    def _seed_companies(self):
        """초기 회사 시드 데이터 삽입 (이미 시드된 회사는 건너뜀)."""
        for company in COMPANY_SEEDS:
            cursor = self.conn.execute(
                'SELECT id FROM companies WHERE name = ?', (company["name"],)
            )
            if cursor.fetchone() is not None:
                continue
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.conn.execute(
                '''INSERT INTO companies
                   (name, aliases, industry, talent_profile, business_focus,
                    recent_news_summary, recruiting_status, source_urls, last_updated, is_cached)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)''',
                (
                    company["name"],
                    company.get("aliases", ""),
                    company.get("industry", ""),
                    company.get("talent_profile", ""),
                    company.get("business_focus", ""),
                    company.get("recent_news_summary", ""),
                    company.get("recruiting_status", ""),
                    company.get("source_urls", ""),
                    now,
                ),
            )
        self.conn.commit()

    def get_company_info(self, query: str) -> dict | None:
        """회사명으로 캐시된 정보 조회. name·aliases 모두 검색.

        Args:
            query: 사용자가 입력한 회사명 (정식명/약칭/영문 등)

        Returns:
            dict | None: 회사 정보 dict 또는 캐시 미스 시 None
        """
        if not query or not query.strip():
            return None
        q = query.strip()
        # 정확 일치 우선
        cursor = self.conn.execute(
            'SELECT * FROM companies WHERE name = ?', (q,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        # aliases LIKE 검색
        cursor = self.conn.execute(
            "SELECT * FROM companies WHERE aliases LIKE ? OR name LIKE ?",
            (f"%{q}%", f"%{q}%"),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def upsert_company_info(self, info: dict) -> int:
        """회사 정보 신규 삽입 또는 갱신.

        Args:
            info: name 필수, 나머지 필드 선택

        Returns:
            int: 회사 레코드 ID
        """
        if not info.get("name"):
            raise ValueError("name is required")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self.conn.execute(
            'SELECT id FROM companies WHERE name = ?', (info["name"],)
        )
        existing = cursor.fetchone()
        if existing:
            self.conn.execute(
                '''UPDATE companies
                   SET aliases = ?, industry = ?, talent_profile = ?, business_focus = ?,
                       recent_news_summary = ?, recruiting_status = ?, source_urls = ?,
                       last_updated = ?, is_cached = ?
                   WHERE id = ?''',
                (
                    info.get("aliases", ""),
                    info.get("industry", ""),
                    info.get("talent_profile", ""),
                    info.get("business_focus", ""),
                    info.get("recent_news_summary", ""),
                    info.get("recruiting_status", ""),
                    info.get("source_urls", ""),
                    now,
                    1 if info.get("is_cached", True) else 0,
                    existing[0],
                ),
            )
            self.conn.commit()
            return existing[0]
        cursor = self.conn.execute(
            '''INSERT INTO companies
               (name, aliases, industry, talent_profile, business_focus,
                recent_news_summary, recruiting_status, source_urls, last_updated, is_cached)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                info["name"],
                info.get("aliases", ""),
                info.get("industry", ""),
                info.get("talent_profile", ""),
                info.get("business_focus", ""),
                info.get("recent_news_summary", ""),
                info.get("recruiting_status", ""),
                info.get("source_urls", ""),
                now,
                1 if info.get("is_cached", True) else 0,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def list_cached_companies(self) -> list[dict]:
        """캐시된 회사 목록 (자동완성용).

        Returns:
            list[dict]: name, industry, last_updated
        """
        cursor = self.conn.execute(
            'SELECT name, industry, last_updated FROM companies WHERE is_cached = 1 ORDER BY name'
        )
        return [dict(row) for row in cursor.fetchall()]
