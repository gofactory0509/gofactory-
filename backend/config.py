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
    allowed_origins: list[str] = ["http://localhost:8000", "*"]
    host: str = "0.0.0.0"
    port: int = 8000

    # Bedrock 라우터 측이 직접 환경변수에서 읽으므로 Settings에는 미선언이지만
    # 동일 .env 파일을 공유하므로 extra=ignore로 거부 방지.
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
