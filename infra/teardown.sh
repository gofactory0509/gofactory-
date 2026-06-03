#!/usr/bin/env bash
# =============================================================================
# Go터뷰 크롤러 인프라 제거 스크립트
# =============================================================================
# 사용법:
#   export AWS_ACCOUNT_ID=... AWS_REGION=us-east-1 S3_BUCKET=gofactory-companies
#   ./infra/teardown.sh             # 모든 리소스 제거 (S3 데이터 포함)
#   ./infra/teardown.sh --keep-data # S3 bucket + Secret 만 유지
# =============================================================================

set -euo pipefail

KEEP_DATA="false"
if [[ "${1:-}" == "--keep-data" ]]; then
  KEEP_DATA="true"
fi

REQUIRED_VARS=(AWS_ACCOUNT_ID AWS_REGION S3_BUCKET)
for v in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    echo "[ERROR] 환경변수 누락: $v" >&2
    exit 1
  fi
done

ECR_REPO="gofactory-crawler"
JOB_ROLE_NAME="gofactory-batch-job-role"
EXEC_ROLE_NAME="gofactory-batch-execution-role"
EVENTBRIDGE_ROLE_NAME="gofactory-eventbridge-batch-role"
COMPUTE_ENV="gofactory-crawler-ce"
JOB_QUEUE="gofactory-crawler-queue"
JOB_DEFINITION="gofactory-crawler-job"
EVENT_RULE="gofactory-crawler-weekly"
SNS_TOPIC="gofactory-crawler-failures"
SECRET_NAME="gofactory/crawler/api-keys"
DLQ_NAME="gofactory-crawler-dlq"

# ---------- 확인 prompt ----------
cat <<EOF
================================================================
  WARNING: Go터뷰 크롤러 인프라 제거
================================================================
  Region:   ${AWS_REGION}
  Account:  ${AWS_ACCOUNT_ID}
  Mode:     $( [[ "$KEEP_DATA" == "true" ]] && echo "데이터 유지 (S3/Secret 보존)" || echo "전체 삭제 (S3/Secret 포함)" )

  삭제 대상:
    - Batch Job Definition / Queue / Compute Env
    - EventBridge Rule + Target + DLQ(SQS)
    - SNS Topic + CloudWatch Alarm
    - IAM Roles + Inline Policies
    - ECR Repository + Images
$( [[ "$KEEP_DATA" == "false" ]] && echo "    - S3 Bucket (${S3_BUCKET}) 전체 + Secret" )
================================================================
EOF
read -rp "정말 삭제하시겠습니까? 'yes' 입력: " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
  echo "취소됨."
  exit 0
fi

soft() { "$@" 2>/dev/null || true; }

echo "[1] EventBridge Rule + DLQ 제거..."
soft aws events remove-targets --rule "$EVENT_RULE" --ids gofactory-crawler-batch-target --region "$AWS_REGION"
soft aws events delete-rule --name "$EVENT_RULE" --region "$AWS_REGION"

DLQ_URL=$(aws sqs get-queue-url --queue-name "$DLQ_NAME" --region "$AWS_REGION" \
  --query 'QueueUrl' --output text 2>/dev/null || echo "")
if [[ -n "$DLQ_URL" ]]; then
  soft aws sqs delete-queue --queue-url "$DLQ_URL" --region "$AWS_REGION"
fi

echo "[2] CloudWatch Alarm + SNS..."
soft aws cloudwatch delete-alarms --alarm-names "gofactory-crawler-job-failures-7d" --region "$AWS_REGION"
SNS_ARN=$(aws sns list-topics --region "$AWS_REGION" \
  --query "Topics[?ends_with(TopicArn, ':${SNS_TOPIC}')].TopicArn | [0]" --output text 2>/dev/null || echo "")
if [[ -n "$SNS_ARN" && "$SNS_ARN" != "None" ]]; then
  soft aws sns delete-topic --topic-arn "$SNS_ARN" --region "$AWS_REGION"
fi

echo "[3] Batch Job Definition / Queue / Compute Env..."
# Job Definitions (모든 revision deregister)
for arn in $(aws batch describe-job-definitions --job-definition-name "$JOB_DEFINITION" \
              --status ACTIVE --region "$AWS_REGION" \
              --query 'jobDefinitions[].jobDefinitionArn' --output text 2>/dev/null || echo ""); do
  soft aws batch deregister-job-definition --job-definition "$arn" --region "$AWS_REGION"
done

# Queue: disable -> delete
soft aws batch update-job-queue --job-queue "$JOB_QUEUE" --state DISABLED --region "$AWS_REGION"
for _ in {1..20}; do
  s=$(aws batch describe-job-queues --job-queues "$JOB_QUEUE" --region "$AWS_REGION" \
        --query 'jobQueues[0].status' --output text 2>/dev/null || echo "NONE")
  [[ "$s" == "VALID" || "$s" == "NONE" ]] && break
  sleep 5
done
soft aws batch delete-job-queue --job-queue "$JOB_QUEUE" --region "$AWS_REGION"

# Compute Env: disable -> delete
soft aws batch update-compute-environment --compute-environment "$COMPUTE_ENV" --state DISABLED --region "$AWS_REGION"
for _ in {1..20}; do
  s=$(aws batch describe-compute-environments --compute-environments "$COMPUTE_ENV" \
        --region "$AWS_REGION" --query 'computeEnvironments[0].status' --output text 2>/dev/null || echo "NONE")
  [[ "$s" == "VALID" || "$s" == "NONE" ]] && break
  sleep 5
done
soft aws batch delete-compute-environment --compute-environment "$COMPUTE_ENV" --region "$AWS_REGION"

echo "[4] IAM roles..."
for role in "$JOB_ROLE_NAME" "$EXEC_ROLE_NAME" "$EVENTBRIDGE_ROLE_NAME"; do
  # 인라인 정책 삭제
  for p in $(aws iam list-role-policies --role-name "$role" --query 'PolicyNames[]' --output text 2>/dev/null || echo ""); do
    soft aws iam delete-role-policy --role-name "$role" --policy-name "$p"
  done
  # attach 된 정책 detach (혹시)
  for p in $(aws iam list-attached-role-policies --role-name "$role" \
              --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null || echo ""); do
    soft aws iam detach-role-policy --role-name "$role" --policy-arn "$p"
  done
  soft aws iam delete-role --role-name "$role"
done

echo "[5] ECR repository + images..."
soft aws ecr delete-repository --repository-name "$ECR_REPO" --force --region "$AWS_REGION"

if [[ "$KEEP_DATA" == "false" ]]; then
  echo "[6] S3 bucket 비우고 삭제..."
  soft aws s3 rm "s3://${S3_BUCKET}" --recursive
  # 버전 객체도 제거
  versions=$(aws s3api list-object-versions --bucket "$S3_BUCKET" \
    --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null || echo "{}")
  if [[ "$versions" != "{}" && "$versions" != "" ]]; then
    echo "$versions" > /tmp/versions.json
    soft aws s3api delete-objects --bucket "$S3_BUCKET" --delete "file:///tmp/versions.json"
  fi
  soft aws s3api delete-bucket --bucket "$S3_BUCKET" --region "$AWS_REGION"

  echo "[7] Secret 삭제..."
  soft aws secretsmanager delete-secret --secret-id "$SECRET_NAME" \
    --force-delete-without-recovery --region "$AWS_REGION"
else
  echo "[6] --keep-data: S3 bucket + Secret 유지"
fi

echo
echo "================================================================"
echo "  Teardown 완료"
echo "================================================================"
