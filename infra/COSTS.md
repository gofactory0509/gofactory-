# 월별 비용 추정 (us-east-1, 2026-06 기준)

> 기준: 매주 1회 실행 (월 약 4회), 1회당 약 5분, 1 vCPU + 2 GB RAM, Fargate Spot.

## 항목별

| 서비스 | 단가 | 사용량 (월) | 월 비용 |
|--------|------|-------------|---------|
| **AWS Batch (Fargate Spot) - vCPU** | $0.01265 / vCPU·hour | 1 vCPU × 5분 × 4회 = 0.333 vCPU·hr | $0.0042 |
| **AWS Batch (Fargate Spot) - Memory** | $0.00138 / GB·hour | 2 GB × 5분 × 4회 = 0.667 GB·hr | $0.0009 |
| **ECR 저장소** | $0.10 / GB·month | 이미지 ~ 350 MB | $0.04 |
| **S3 Standard 저장** | $0.023 / GB·month | 100 MB × 12 스냅샷 = 1.2 GB | $0.03 |
| **S3 PUT 요청** | $0.005 / 1,000 | 월 4 PUT | $0.00002 |
| **S3 GET 요청 (EC2 pull)** | $0.0004 / 1,000 | 월 30 GET | $0.00001 |
| **CloudWatch Logs ingestion** | $0.50 / GB | 월 100 MB | $0.05 |
| **CloudWatch Logs 저장 (30일)** | $0.03 / GB·month | 0.1 GB | $0.003 |
| **CloudWatch Alarm** | $0.10 / alarm·month | 1 alarm | $0.10 |
| **SNS - 알림 publish** | $0.50 / 1M (email) | < 5 / 월 | $0.00 (free tier) |
| **EventBridge Rule** | $1.00 / 1M custom events | 4 events / 월 | $0.00 |
| **SQS DLQ** | $0.40 / 1M 요청 | < 5 / 월 | $0.00 (free tier) |
| **Secrets Manager** | $0.40 / secret·month + $0.05 / 10K API call | 1 secret + ~ 4 calls | $0.40 |
| **Bedrock - Claude Sonnet 4.6 input** | $3 / 1M tokens | 회사 5개 × 평균 5K in = 25K × 4 = 100K | $0.30 |
| **Bedrock - Claude Sonnet 4.6 output** | $15 / 1M tokens | 회사 5개 × 평균 2K out = 10K × 4 = 40K | $0.60 |
| **데이터 전송 (Egress)** | 첫 100GB 무료 | < 1 GB | $0.00 |

## 합계

| 카테고리 | 월 비용 |
|----------|---------|
| 컴퓨트 (Batch Fargate Spot) | **$0.005** |
| 저장 (ECR + S3 + Logs) | **$0.12** |
| 모니터링 (CW Alarm + SNS + EventBridge) | **$0.10** |
| 비밀 관리 (Secrets Manager) | **$0.40** |
| AI 추론 (Bedrock Claude Sonnet 4.6) | **$0.90** |
| **합계** | **약 $1.53 / 월** |

> 참고: Bedrock 토큰 사용량이 비용 대부분 차지. 크롤러 측에서 회사당 LLM 호출 횟수·토큰 길이를 최적화하면 $0.50 미만으로 줄일 수 있음.
>
> 만약 LLM 사용을 빼면 (정형 크롤링만): **월 $0.65 미만**.
>
> 만약 LLM도 빼고 Secrets Manager도 Parameter Store(무료)로 옮기면: **월 $0.25 미만**.

## 비용 절감 옵션

1. **Bedrock 캐싱** — 회사 description 같은 정적 컨텍스트는 prompt cache 적용 (input 비용 90% 절감)
2. **CloudWatch Alarm 제거** — Batch job 실패 이벤트를 EventBridge -> SNS로 직접 라우팅하면 alarm $0.10 절약
3. **Secrets Manager -> SSM Parameter Store** — SecureString 무료 (단 자동 회전 X)
4. **로그 보관 기간 단축** — 30일 -> 7일로 줄이면 저장 비용 75% 절감
5. **ECR 라이프사이클 정책** — 최신 3개만 유지 (이미지 storage 90% 절감)

## 무료 영역

- AWS Batch 자체는 무료 (Fargate 컴퓨트만 과금)
- CloudWatch Metric 기본 무료
- IAM 무료
- VPC / Subnet / SG 무료 (NAT Gateway 쓰면 별도)

## 주의

- **NAT Gateway 사용 시** 추가 비용 발생 ($0.045 / hour × 720h = **$32 / 월**). 본 인프라는 public subnet + assignPublicIp=ENABLED로 NAT 회피.
- **Bedrock 모델 액세스 미활성화 상태에서 InvokeModel 호출 -> 실패** (요금 X, 단 알람 발생).
- Free Tier (계정 첫 12개월): CloudWatch Logs 5GB 무료, S3 5GB 무료. 본 인프라는 Free Tier 내 충분히 수용.
