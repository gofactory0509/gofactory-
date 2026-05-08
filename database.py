"""면접 기록 데이터베이스 모듈.

SQLite를 사용하여 면접 질문, 답변, 피드백을 저장하고 조회한다.
"""

import sqlite3
from datetime import datetime


class InterviewDB:
    """면접 기록 SQLite 데이터베이스.

    면접 세션의 질문, 답변, 피드백을 저장하고 조회하는 기능을 제공한다.
    """

    def __init__(self, db_path: str = "interviews.db"):
        """데이터베이스 연결 및 테이블 생성.

        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        """면접 기록 테이블 생성."""
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

    def close(self):
        """데이터베이스 연결 종료."""
        self.conn.close()
