# -*- coding: utf-8 -*-
"""면접 기록 데이터베이스 모듈.

SQLite를 사용하여 면접 질문, 답변, 피드백을 저장하고 조회한다.
common_questions 테이블로 직무별 기출 질문을 관리한다.
"""

import sqlite3
from datetime import datetime


# 직무별 사전 등록 면접 질문
SEED_QUESTIONS = {
    "반도체": [
        ("반도체 공정에서 식각(Etching)의 종류와 차이점을 설명해주세요.", "중"),
        ("MOSFET의 동작 원리를 간단히 설명해주세요.", "중"),
        ("반도체 수율(Yield)을 높이기 위한 방법에는 어떤 것들이 있나요?", "상"),
        ("CVD와 PVD의 차이점을 설명해주세요.", "중"),
        ("반도체 미세공정에서 EUV 리소그래피가 필요한 이유는 무엇인가요?", "상"),
        ("PN 접합 다이오드의 순방향/역방향 바이어스 특성을 설명해주세요.", "하"),
        ("클린룸에서 파티클 관리가 중요한 이유를 설명해주세요.", "하"),
    ],
    "백엔드": [
        ("REST API와 GraphQL의 차이점과 각각의 장단점을 설명해주세요.", "중"),
        ("데이터베이스 인덱스의 동작 원리와 사용 시 주의점을 설명해주세요.", "중"),
        ("마이크로서비스 아키텍처의 장단점을 모놀리식과 비교하여 설명해주세요.", "상"),
        ("트랜잭션의 ACID 속성을 설명하고 실무 예시를 들어주세요.", "중"),
        ("대용량 트래픽 처리를 위한 서버 확장 전략을 설명해주세요.", "상"),
        ("HTTP 상태 코드 중 자주 사용하는 것들과 의미를 설명해주세요.", "하"),
        ("JWT 토큰 기반 인증의 동작 방식과 장단점을 설명해주세요.", "중"),
    ],
    "데이터": [
        ("정규화와 비정규화의 차이점과 각각 언제 사용하는지 설명해주세요.", "중"),
        ("ETL 파이프라인 설계 시 고려해야 할 사항을 설명해주세요.", "상"),
        ("A/B 테스트 설계 시 주의할 점과 통계적 유의성 판단 기준을 설명해주세요.", "상"),
        ("데이터 웨어하우스와 데이터 레이크의 차이점을 설명해주세요.", "중"),
        ("SQL에서 윈도우 함수의 활용 사례를 설명해주세요.", "중"),
        ("데이터 품질을 관리하기 위한 방법론을 설명해주세요.", "중"),
        ("배치 처리와 실시간 처리의 차이점과 적합한 사용 사례를 설명해주세요.", "상"),
    ],
    "마케팅": [
        ("퍼포먼스 마케팅에서 ROAS와 ROI의 차이를 설명해주세요.", "중"),
        ("고객 퍼널(Funnel) 분석의 각 단계와 개선 전략을 설명해주세요.", "중"),
        ("CRM 마케팅에서 고객 세그먼테이션 전략을 설명해주세요.", "상"),
        ("콘텐츠 마케팅의 KPI 설정 방법과 측정 지표를 설명해주세요.", "중"),
        ("브랜드 포지셔닝 전략을 수립하는 과정을 설명해주세요.", "상"),
        ("디지털 마케팅에서 리타겟팅의 원리와 효과적인 활용법을 설명해주세요.", "중"),
        ("마케팅 예산 배분 시 고려해야 할 요소들을 설명해주세요.", "중"),
    ],
}


class InterviewDB:
    """면접 기록 SQLite 데이터베이스.

    면접 세션의 질문, 답변, 피드백을 저장하고 조회하는 기능을 제공한다.
    직무별 기출 질문 관리 및 통계 기능을 포함한다.
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

    def _create_tables(self):
        """면접 기록 및 질문 뱅크 테이블 생성."""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS interviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                job_field TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                feedback TEXT NOT NULL,
                score INTEGER
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
        self.conn.commit()

    def _seed_common_questions(self):
        """사전 등록 질문이 없으면 초기 데이터 삽입."""
        cursor = self.conn.execute('SELECT COUNT(*) FROM common_questions')
        count = cursor.fetchone()[0]
        if count > 0:
            return

        for job_field, questions in SEED_QUESTIONS.items():
            for question_text, difficulty in questions:
                self.conn.execute(
                    'INSERT INTO common_questions (job_field, question, difficulty) VALUES (?, ?, ?)',
                    (job_field, question_text, difficulty)
                )
        self.conn.commit()

    def save_interview(self, job_field: str, question: str, answer: str, feedback: str, score: int | None = None):
        """면접 기록 저장.

        Args:
            job_field: 직무 분야
            question: 면접 질문
            answer: 사용자 답변
            feedback: AI 피드백
            score: 논리성 점수 (선택)
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute(
            '''INSERT INTO interviews (date, job_field, question, answer, feedback, score)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (now, job_field, question, answer, feedback, score)
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

    def close(self):
        """데이터베이스 연결 종료."""
        self.conn.close()
