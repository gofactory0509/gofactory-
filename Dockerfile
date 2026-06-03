# =============================================================================
# Go터뷰 회사 크롤러 컨테이너 (AWS Batch / Fargate Spot)
# =============================================================================
# 멀티스테이지 빌드로 슬림화.
# - builder: 빌드 도구 + pip wheel 생성
# - runtime: wheel 만 복사한 슬림 이미지
#
# ENTRYPOINT: python scripts/crawl_companies.py
# EventBridge -> Batch -> 이 컨테이너 -> S3 스냅샷 업로드
# =============================================================================

# ----- Stage 1: builder -----
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libffi-dev \
        && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# requirements.txt만 먼저 복사 (레이어 캐시)
COPY requirements.txt ./

# Wheel로 빌드 (slim runtime에서 컴파일 불필요)
RUN pip wheel --wheel-dir=/wheels -r requirements.txt

# ----- Stage 2: runtime -----
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AWS_REGION=us-east-1 \
    BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-6-20251015-v1:0 \
    S3_BUCKET=gofactory-companies \
    OUTPUT_DB_PATH=/tmp/companies.db

# AWS CLI v2 (S3 업로드용 - 슬림 설치)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        unzip \
        && curl -sSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip \
        && unzip -q /tmp/awscliv2.zip -d /tmp \
        && /tmp/aws/install \
        && rm -rf /tmp/aws /tmp/awscliv2.zip \
        && apt-get purge -y unzip curl \
        && apt-get autoremove -y \
        && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# builder에서 만든 wheel 가져와서 설치
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN pip install --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# 앱 코드 복사 (크롤러 관련만)
COPY scripts/ ./scripts/
COPY backend/ ./backend/
COPY config.py ./
COPY ai_client.py ./
COPY database.py ./

# 비root 유저
RUN useradd --create-home --shell /bin/bash crawler \
    && chown -R crawler:crawler /app
USER crawler

# 진입점: 크롤러 스크립트. 인자는 Job Definition의 command로 override 가능.
ENTRYPOINT ["python", "scripts/crawl_companies.py"]
CMD ["--companies", "삼성전자,SK하이닉스,DB하이텍,한미반도체,솔브레인", \
     "--output", "/tmp/companies.db", \
     "--upload-s3"]
