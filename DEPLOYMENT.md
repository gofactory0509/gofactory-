# Go터뷰 EC2 배포 가이드

> 대상: EC2 `34.227.222.133` (us-east-1 추정)
> 백엔드: FastAPI + AWS Bedrock (Claude Sonnet 4.6 기본) + OpenRouter (사용자 BYOK)

---

## 0. 사전 준비 (AWS 콘솔 작업)

### 0-1. Bedrock 모델 access 활성화
1. AWS Console → **Amazon Bedrock** → 좌측 **Model access**
2. **Anthropic Claude Sonnet 4.6** → Request access (보통 즉시 승인)
3. EC2와 같은 region (us-east-1)에서 활성화

### 0-2. EC2 IAM Role 부착
1. **IAM** → **Roles** → Create role
2. Use case: **EC2**
3. Permissions: `AmazonBedrockFullAccess` (또는 inline policy로 최소 권한)
4. Role 이름 예: `gofactory-ec2-bedrock`
5. EC2 인스턴스 → Actions → Security → **Modify IAM role** → 위 Role 부착

### 0-3. 보안 그룹 (Security Group)
- Inbound: SSH(22), HTTP(80), HTTPS(443), FastAPI(8000) 본인 IP에서만
- 발표·시연 시 8000번을 0.0.0.0/0으로 임시 개방 가능 (이후 nginx로 80→8000 프록시 권장)

---

## 1. EC2 첫 접속 및 환경 셋업

### 1-1. SSH 접속
```bash
ssh -i your-key.pem ec2-user@34.227.222.133
# Ubuntu AMI라면 ubuntu@34.227.222.133
```

### 1-2. 시스템 패키지
**Amazon Linux 2023 기준:**
```bash
sudo dnf update -y
sudo dnf install -y python3.11 python3.11-pip git nginx
```

**Ubuntu 기준:**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx
```

### 1-3. 코드 받기
```bash
cd ~
git clone https://github.com/gofactory0509/gofactory-.git gofactory
cd gofactory
git checkout feature/v3-domain-specialization
```

### 1-4. Python 가상환경 + 의존성
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 1-5. 환경 변수
```bash
cp .env.example .env
nano .env
```

`.env` 내용:
```bash
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-6-20251015-v1:0
# AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY 는 IAM Role 사용 시 불필요
```

> ⚠️ Bedrock model ID는 AWS Console → Bedrock → Model catalog에서 정확한 ID 확인 후 입력

---

## 2. 실행 테스트

### 2-1. FastAPI 직접 실행
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

브라우저: `http://34.227.222.133:8000/docs` → Swagger UI 표시되면 OK.

### 2-2. Bedrock 동작 확인
SSH 안에서:
```bash
python -c "
from backend.services.bedrock_client import BedrockClient
c = BedrockClient()
print(c.generate('한국어로 자기소개 한 줄 해줘.'))
"
```

기대 출력: 한국어 자기소개 한 줄
실패 시 점검:
- `boto3.client('sts').get_caller_identity()` → IAM Role 확인
- Bedrock 콘솔 Model access 활성화 여부
- region 일치 여부

---

## 3. 백그라운드 실행 (systemd)

### 3-1. systemd unit 작성
```bash
sudo nano /etc/systemd/system/gofactory.service
```

내용:
```ini
[Unit]
Description=Go터뷰 FastAPI
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/gofactory
EnvironmentFile=/home/ec2-user/gofactory/.env
ExecStart=/home/ec2-user/gofactory/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 3-2. 활성화
```bash
sudo systemctl daemon-reload
sudo systemctl enable gofactory
sudo systemctl start gofactory
sudo systemctl status gofactory     # 정상 동작 확인
sudo journalctl -u gofactory -f     # 실시간 로그
```

---

## 4. (선택) Nginx 리버스 프록시

`http://34.227.222.133` (포트 80) 로 접속할 수 있게.

```bash
sudo nano /etc/nginx/conf.d/gofactory.conf
```

```nginx
server {
    listen 80;
    server_name 34.227.222.133;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 정적 frontend (선택)
    location /static/ {
        alias /home/ec2-user/gofactory/frontend/;
    }
}
```

```bash
sudo nginx -t
sudo systemctl restart nginx
```

이후 `http://34.227.222.133` 접속 시 FastAPI로 프록시.

---

## 5. 변경 사항 배포 (개발 → 운영)

로컬에서 push 후 EC2에서:
```bash
cd ~/gofactory
git pull
source .venv/bin/activate
pip install -r requirements.txt   # 의존성 변경 시
sudo systemctl restart gofactory
sudo journalctl -u gofactory -f   # 재시작 확인
```

---

## 6. 비용 모니터링

### 일일 비용 확인
- AWS Console → **Billing & Cost Management** → Cost Explorer
- 필터: Service = "Amazon Bedrock"

### 예상 비용 (Sonnet 4.6 기준)
- 면접 1회 ≈ 입력 3K + 출력 1K 토큰 → **~$0.024** ($3 × 3K + $15 × 1K = 0.009 + 0.015)
- $100 크레딧 = 약 **4,000회** 면접 가능

### 알림 설정
- Billing → Budgets → Create budget → 월 $20 한도 + 50%/80%/100% 알림 이메일

---

## 7. 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `AccessDeniedException` | IAM Role 권한 부족 | IAM Role에 `bedrock:InvokeModel` 추가 |
| `ValidationException: model not found` | model ID 오타 또는 region 불일치 | Bedrock 콘솔에서 정확한 ID 복사 |
| `ThrottlingException` | rate limit | Sonnet quota 신청 또는 Haiku로 fallback |
| `ConnectionError` | 보안 그룹 차단 | SG inbound 규칙 확인 |
| systemd 시작 실패 | venv 경로 오류 | `ExecStart` 절대 경로 확인 |

---

## 8. 보안 체크리스트 (운영 전 필수)

- [ ] `.env` 파일 권한 600 (`chmod 600 .env`)
- [ ] SSH 키 미공유, 보안그룹 22번 본인 IP만 허용
- [ ] HTTPS 적용 (Let's Encrypt + certbot, 도메인 있을 시)
- [ ] AWS IAM 최소 권한 정책 적용
- [ ] CloudWatch 로그 활성화
- [ ] 일일 비용 알림 활성화
- [ ] DB(interviews.db) 정기 백업 (S3로)
