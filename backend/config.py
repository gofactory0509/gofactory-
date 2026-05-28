"""환경 설정 모듈

Pydantic BaseSettings를 사용하여 환경 변수를 타입 안전하게 로드한다.
설정 우선순위: 환경 변수 > .env 파일 > 기본값
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정

    Attributes:
        gemini_api_key: Google Gemini API 키 (기본 AI 모델)
        groq_api_key: Groq API 키 (Gemini 실패 시 폴백 모델)
        database_path: SQLite 데이터베이스 파일 경로
        allowed_origins: CORS 허용 오리진 목록
        host: 서버 바인딩 호스트
        port: 서버 바인딩 포트
    """

    gemini_api_key: str = ""
    groq_api_key: str = ""
    database_path: str = "interviews.db"
    allowed_origins: list[str] = ["http://localhost:8000"]
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
