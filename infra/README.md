# Go터뷰 크롤러 인프라 (AWS Batch + EventBridge)

매주 일요일 02:00 KST (= UTC 17:00 토)에 5개 시드 회사 정보를 크롤링하여 S3에 스냅샷으로 업로드하는 정기 파이프라인.

```
EventBridge cron(0 17 ? * SAT *)
   -> AWS Batch (Fargate Spot)
   -> Container: python scripts/crawl_companies.py
   -> S3: s3://gofactory-companies/snapshots/{date}.db
   -> (별도 systemd timer) EC2가 새벽에 pull -> interviews.db 업데이트
```

---

## 1. 사전 준비

### 1.1 로컬 도구
- AWS CLI v2 (`aws --version` -> v2.x)
- Docker (BuildKit 권장)
- jq (`brew install jq` / `apt install jq` / Windows: scoop/choco)
- bash (Windows에서는 Git Bash 또는 WSL)

### 1.2 AWS 계정 사전 작업
- **VPC + 퍼블릭 Subnet 2개 이상** (Fargate Spot이 ENI 붙일 곳)
- **Security Group** — egress 443/80 허용 (Bedrock·S3·외부 크롤링 API)
- **AWSServiceRoleForBatch** — 한 번도 Batch 안 써봤으면 다음으로 생성:
  ```bash
  aws iam create-service-linked-role --aws-service-name batch.amazonaws.com || true
  ```
- AWS CLI 자격증명에 `iam:*`, `batch:*`, `events:*`, `ecr:*`, `s3:*`, `secretsmanager:*`, `sns:*`, `cloudwatch:*`, `sqs:*`, `logs:*` 권한 필요 (관리자 계정 권장)

---

## 2. 환경변수 export

`.envrc` 예시 (절대 git에 커밋하지 말 것 — `.gitignore`에 추가):

```bash
# ===== 필수 =====
export AWS_ACCOUNT_ID=123456789012
export AWS_REGION=us-east-1
export SUBNETS="subnet-0aaaaaaaaaaaaaaaa,subnet-0bbbbbbbbbbbbbbbb"
export SECURITY_GROUPS="sg-0cccccccccccccccc"
export S3_BUCKET=gofactory-companies
export ALERT_EMAIL=kimseng070824@gmail.com

# ===== 선택 =====
export IMAGE_TAG=latest                 # 기본 latest
export SECRETS_FILE=./secrets.env       # 미설정 시 deploy.sh가 prompt

# secrets.env 형식 예 (역시 커밋 금지)
# NAVER_CLIENT_ID=xxxxxxxx
# NAVER_CLIENT_SECRET=xxxxxxxx
# DART_API_KEY=xxxxxxxx
```

```bash
source .envrc
```

---

## 3. 배포

```bash
chmod +x infra/deploy.sh infra/teardown.sh infra/redeploy-image.sh
./infra/deploy.sh
```

스크립트는 idempotent — 이미 있으면 update / skip. 약 5~10분 소요 (Docker 이미지 빌드 + Batch CE VALID 대기 포함).

### 단계 요약
| # | 단계 | 동작 |
|---|------|------|
| 1 | ECR | repo create (또는 skip) |
| 2 | Docker | build, tag, push |
| 3 | IAM | job role / exec role / eventbridge role + inline policies |
| 4 | S3 | bucket (versioned, private) |
| 5 | Secrets | gofactory/crawler/api-keys 생성/갱신 |
| 6 | CloudWatch | `/aws/batch/job` log group + 30d retention |
| 7 | Batch | Compute Env + Queue + Job Definition |
| 8 | EventBridge | Rule + Target + SQS DLQ |
| 9 | SNS | topic + email subscribe + CloudWatch Alarm |

배포 후 등록한 이메일로 "AWS Notification - Subscription Confirmation" 메일이 옴 -> Confirm 클릭 필요.

---

## 4. 테스트 트리거 (수동 실행)

```bash
aws batch submit-job \
  --job-name gofactory-crawler-manual-$(date +%s) \
  --job-queue gofactory-crawler-queue \
  --job-definition gofactory-crawler-job \
  --region us-east-1
```

상태 확인:
```bash
aws batch list-jobs --job-queue gofactory-crawler-queue --region us-east-1
aws batch describe-jobs --jobs <JOB_ID> --region us-east-1 \
  --query 'jobs[0].{status:status,reason:statusReason}'
```

EventBridge 동작 확인 (다음 실행 예정):
```bash
aws events describe-rule --name gofactory-crawler-weekly --region us-east-1
```

---

## 5. 로그 확인

### 실시간 tail
```bash
aws logs tail /aws/batch/job --follow --region us-east-1 \
  --filter-pattern "gofactory-crawler"
```

### CloudWatch Logs Insights 쿼리

**최근 24시간 에러만:**
```
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100
```

**회사별 크롤링 소요 시간:**
```
fields @timestamp, @message
| parse @message "[*] company=* elapsed=*ms" as level, company, elapsed
| stats avg(elapsed), max(elapsed), count() by company
```

**S3 업로드 결과:**
```
fields @timestamp, @message
| filter @message like /s3:\/\/gofactory-companies/
| sort @timestamp desc
```

---

## 6. EC2에서 S3 pull 받기 (별도 작업)

EC2 인스턴스 (34.227.222.133)가 매일 새벽 03:00 KST에 최신 스냅샷을 받아 `interviews.db`를 갱신.

`/etc/systemd/system/gofactory-sync.service`:
```ini
[Unit]
Description=Pull latest companies.db snapshot from S3
After=network-online.target

[Service]
Type=oneshot
User=ec2-user
ExecStart=/usr/local/bin/gofactory-sync.sh
```

`/etc/systemd/system/gofactory-sync.timer`:
```ini
[Unit]
Description=Daily companies.db sync at 03:00 KST

[Timer]
OnCalendar=*-*-* 18:00:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
```

`/usr/local/bin/gofactory-sync.sh`:
```bash
#!/bin/bash
set -euo pipefail
BUCKET=gofactory-companies
LATEST=$(aws s3 ls "s3://${BUCKET}/snapshots/" | sort | tail -n1 | awk '{print $4}')
aws s3 cp "s3://${BUCKET}/snapshots/${LATEST}" /tmp/companies.db
# 원자적 교체
mv /tmp/companies.db /opt/gofactory/companies.db.new
mv /opt/gofactory/companies.db.new /opt/gofactory/companies.db
systemctl reload gofactory-api || true
```

활성화:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gofactory-sync.timer
```

EC2 측 IAM (`SafeInstanceProfile-pj-kmuai-02`)에 다음 권한 필요:
- `s3:ListBucket` on `arn:aws:s3:::gofactory-companies`
- `s3:GetObject` on `arn:aws:s3:::gofactory-companies/snapshots/*`

---

## 7. 트러블슈팅

| 증상 | 원인 / 해결 |
|------|-----------|
| `CLIENT_ERROR: Resourcerequirements is invalid` | vCPU/Memory 조합이 Fargate 유효값 아님. 1vCPU + 2048MiB는 OK |
| `CannotPullContainerError` | Execution Role 의 ECR 권한 누락 / 서브넷이 인터넷 outbound 불가 (NAT 또는 public IP 필요) |
| Job이 RUNNABLE 에서 안 움직임 | Compute Env가 INVALID — `aws batch describe-compute-environments`로 statusReason 확인 (대개 subnet/SG 잘못) |
| `AccessDeniedException: bedrock:InvokeModel` | us-east-1에서 Claude Sonnet 4.6 모델 액세스 활성화 안 됨 — Bedrock 콘솔 -> Model access에서 허용 |
| `secretsmanager:GetSecretValue denied` | Execution Role에 SecretsManager 권한 누락 (deploy.sh가 이미 부여) — IAM 전파 지연일 수도 (10초 sleep 있음) |
| EventBridge 실행 후 RUNNING 안 됨 | DLQ(SQS) 확인 -> 실패 이벤트의 ErrorMessage 확인 |
| SNS 이메일 안 옴 | "Subscription confirmation" 메일에서 Confirm 누르지 않음 / 스팸함 확인 |
| 이미지 push 시 `denied: requested access` | `aws ecr get-login-password` 만료 — deploy.sh 다시 실행 |

---

## 8. 운영

**이미지만 재배포:**
```bash
./infra/redeploy-image.sh
# 또는 새 tag로
IMAGE_TAG=v1.2 ./infra/redeploy-image.sh
```

**전체 제거:**
```bash
./infra/teardown.sh              # S3/Secret 포함 전체 삭제
./infra/teardown.sh --keep-data  # 데이터는 보존
```

**일시 정지:**
```bash
aws events disable-rule --name gofactory-crawler-weekly --region us-east-1
# 재개
aws events enable-rule  --name gofactory-crawler-weekly --region us-east-1
```

---

## 9. 파일 구조

```
infra/
├── batch/
│   ├── compute-environment.json    # FARGATE_SPOT, maxvCpus=4
│   ├── job-queue.json
│   └── job-definition.json         # 1vCPU, 2GB, secrets, env
├── eventbridge/
│   ├── rule.json                   # cron(0 17 ? * SAT *)
│   └── target.json                 # Batch + DLQ
├── iam/
│   ├── batch-job-role-policy.json       # Bedrock + S3 + Secrets + Logs
│   ├── batch-execution-role-policy.json # ECR pull + Logs + Secrets 주입
│   ├── batch-task-trust-policy.json     # ecs-tasks.amazonaws.com
│   └── eventbridge-batch-trust-policy.json
├── sns/
│   └── failure-alert-topic.json
├── deploy.sh
├── teardown.sh
├── redeploy-image.sh
├── README.md
└── COSTS.md
```

## 10. 보안 메모
- API 키는 Secrets Manager에서만 관리. 컨테이너 환경변수로 평문 노출 X.
- S3 bucket은 BlockPublicAcls=ON, 버전 관리 활성화.
- Bedrock 권한은 Sonnet 4.6 모델 ARN 패턴으로만 제한.
- IAM 정책은 모두 인라인 (role 삭제 시 함께 제거).
- ECR 이미지는 push 시 자동 스캔.
