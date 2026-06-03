#!/usr/bin/env bash
# =============================================================================
# Go터뷰 크롤러 인프라 일괄 배포 스크립트 (idempotent)
# =============================================================================
# 사용법:
#   export AWS_ACCOUNT_ID=123456789012
#   export AWS_REGION=us-east-1
#   export SUBNETS="subnet-aaa,subnet-bbb"
#   export SECURITY_GROUPS="sg-xxx"
#   export S3_BUCKET=gofactory-companies
#   export ALERT_EMAIL=kimseng070824@gmail.com
#   # (선택) export SECRETS_FILE=./secrets.env  -> 없으면 prompt
#   ./infra/deploy.sh
#
# 각 단계는 idempotent. 이미 존재하면 skip / update.
# =============================================================================

set -euo pipefail

# ---------- 0. 환경변수 체크 ----------
REQUIRED_VARS=(AWS_ACCOUNT_ID AWS_REGION SUBNETS SECURITY_GROUPS S3_BUCKET ALERT_EMAIL)
for v in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    echo "[ERROR] 환경변수 누락: $v" >&2
    echo "참고: infra/README.md 의 '환경변수 export' 섹션" >&2
    exit 1
  fi
done

# 의존 도구 체크
for cmd in aws docker jq; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[ERROR] 필수 도구 누락: $cmd" >&2
    exit 1
  fi
done

# 상수
ECR_REPO="gofactory-crawler"
IMAGE_TAG="${IMAGE_TAG:-latest}"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"
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
LOG_GROUP="/aws/batch/job"

INFRA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${INFRA_DIR}/.." && pwd)"

# 치환 함수: REPLACE_WITH_ACCOUNT_ID -> 실제 account id
render_json() {
  local src="$1"
  local dst="$2"
  sed \
    -e "s|REPLACE_WITH_ACCOUNT_ID|${AWS_ACCOUNT_ID}|g" \
    "$src" > "$dst"
}

# subnets/SGs: comma-separated -> JSON array
subnets_json="$(echo "$SUBNETS"        | jq -R 'split(",")')"
sgs_json="$(    echo "$SECURITY_GROUPS" | jq -R 'split(",")')"

echo "================================================================"
echo "  Go터뷰 크롤러 인프라 배포 시작"
echo "  Account: ${AWS_ACCOUNT_ID}  Region: ${AWS_REGION}"
echo "================================================================"

# ---------- 1. ECR repo ----------
echo "[1/9] ECR repository..."
if ! aws ecr describe-repositories --repository-names "$ECR_REPO" --region "$AWS_REGION" >/dev/null 2>&1; then
  aws ecr create-repository \
    --repository-name "$ECR_REPO" \
    --image-scanning-configuration scanOnPush=true \
    --region "$AWS_REGION" >/dev/null
  echo "  -> created"
else
  echo "  -> exists, skip"
fi

# ---------- 2. Docker build / push ----------
echo "[2/9] Docker build + push..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com" >/dev/null

(cd "$REPO_ROOT" && docker build -t "${ECR_REPO}:${IMAGE_TAG}" .)
docker tag "${ECR_REPO}:${IMAGE_TAG}" "${ECR_URI}:${IMAGE_TAG}"
docker push "${ECR_URI}:${IMAGE_TAG}"
echo "  -> pushed ${ECR_URI}:${IMAGE_TAG}"

# ---------- 3. IAM roles ----------
echo "[3/9] IAM roles..."
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

render_json "${INFRA_DIR}/iam/batch-task-trust-policy.json"        "${TMP_DIR}/batch-task-trust.json"
render_json "${INFRA_DIR}/iam/batch-job-role-policy.json"          "${TMP_DIR}/batch-job-policy.json"
render_json "${INFRA_DIR}/iam/batch-execution-role-policy.json"    "${TMP_DIR}/batch-exec-policy.json"
render_json "${INFRA_DIR}/iam/eventbridge-batch-trust-policy.json" "${TMP_DIR}/eb-trust.json"

create_or_update_role() {
  local role_name="$1"
  local trust_file="$2"
  if aws iam get-role --role-name "$role_name" >/dev/null 2>&1; then
    aws iam update-assume-role-policy --role-name "$role_name" \
      --policy-document "file://$trust_file" >/dev/null
    echo "    $role_name: updated trust"
  else
    aws iam create-role --role-name "$role_name" \
      --assume-role-policy-document "file://$trust_file" \
      --tags Key=Project,Value=gofactory-v3 Key=ManagedBy,Value=deploy.sh >/dev/null
    echo "    $role_name: created"
  fi
}

put_inline_policy() {
  local role_name="$1"
  local policy_name="$2"
  local policy_file="$3"
  aws iam put-role-policy --role-name "$role_name" \
    --policy-name "$policy_name" \
    --policy-document "file://$policy_file" >/dev/null
  echo "    $role_name <- $policy_name"
}

# Batch Job Role (컨테이너 안 권한)
create_or_update_role "$JOB_ROLE_NAME"  "${TMP_DIR}/batch-task-trust.json"
put_inline_policy     "$JOB_ROLE_NAME"  "gofactory-batch-job-inline" "${TMP_DIR}/batch-job-policy.json"

# Batch Execution Role (ECS agent 가 ECR pull / secret 주입)
create_or_update_role "$EXEC_ROLE_NAME" "${TMP_DIR}/batch-task-trust.json"
put_inline_policy     "$EXEC_ROLE_NAME" "gofactory-batch-exec-inline" "${TMP_DIR}/batch-exec-policy.json"

# EventBridge -> Batch role
create_or_update_role "$EVENTBRIDGE_ROLE_NAME" "${TMP_DIR}/eb-trust.json"
# 인라인: BatchSubmitJob
cat > "${TMP_DIR}/eb-submit.json" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["batch:SubmitJob"],
    "Resource": [
      "arn:aws:batch:${AWS_REGION}:${AWS_ACCOUNT_ID}:job-definition/${JOB_DEFINITION}*",
      "arn:aws:batch:${AWS_REGION}:${AWS_ACCOUNT_ID}:job-queue/${JOB_QUEUE}"
    ]
  }]
}
EOF
put_inline_policy "$EVENTBRIDGE_ROLE_NAME" "gofactory-eb-submit-inline" "${TMP_DIR}/eb-submit.json"

# IAM 전파 대기 (eventual consistency)
echo "  -> IAM 전파 대기 10초"
sleep 10

# ---------- 4. S3 bucket ----------
echo "[4/9] S3 bucket: ${S3_BUCKET}"
if aws s3api head-bucket --bucket "$S3_BUCKET" 2>/dev/null; then
  echo "  -> exists, skip"
else
  if [[ "$AWS_REGION" == "us-east-1" ]]; then
    aws s3api create-bucket --bucket "$S3_BUCKET" --region "$AWS_REGION" >/dev/null
  else
    aws s3api create-bucket --bucket "$S3_BUCKET" --region "$AWS_REGION" \
      --create-bucket-configuration "LocationConstraint=$AWS_REGION" >/dev/null
  fi
  aws s3api put-bucket-versioning --bucket "$S3_BUCKET" \
    --versioning-configuration Status=Enabled >/dev/null
  aws s3api put-public-access-block --bucket "$S3_BUCKET" \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" >/dev/null
  echo "  -> created (versioned, private)"
fi

# ---------- 5. Secrets Manager ----------
echo "[5/9] Secrets Manager: ${SECRET_NAME}"
if [[ -n "${SECRETS_FILE:-}" && -f "$SECRETS_FILE" ]]; then
  # 형식: KEY=VALUE per line
  SECRET_JSON="$(awk -F= '/^[A-Z_]+=/{printf "%s\"%s\":\"%s\"", (n++?",":""), $1, substr($0,index($0,"=")+1)}END{print ""}' "$SECRETS_FILE")"
  SECRET_JSON="{${SECRET_JSON}}"
else
  echo "  SECRETS_FILE 미설정 -> 프롬프트로 입력"
  read -rp "  NAVER_CLIENT_ID: "     NAVER_ID
  read -rsp "  NAVER_CLIENT_SECRET: " NAVER_SECRET ; echo
  read -rsp "  DART_API_KEY: "        DART_KEY     ; echo
  SECRET_JSON=$(jq -n \
    --arg ni "$NAVER_ID" --arg ns "$NAVER_SECRET" --arg dk "$DART_KEY" \
    '{NAVER_CLIENT_ID:$ni, NAVER_CLIENT_SECRET:$ns, DART_API_KEY:$dk}')
fi

if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
  aws secretsmanager put-secret-value --secret-id "$SECRET_NAME" \
    --secret-string "$SECRET_JSON" --region "$AWS_REGION" >/dev/null
  echo "  -> updated"
else
  aws secretsmanager create-secret --name "$SECRET_NAME" \
    --description "Go터뷰 크롤러용 외부 API 키" \
    --secret-string "$SECRET_JSON" --region "$AWS_REGION" \
    --tags Key=Project,Value=gofactory-v3 Key=ManagedBy,Value=deploy.sh >/dev/null
  echo "  -> created"
fi

# secret ARN 가져오기
SECRET_ARN=$(aws secretsmanager describe-secret --secret-id "$SECRET_NAME" \
  --region "$AWS_REGION" --query 'ARN' --output text)

# ---------- 6. CloudWatch Log Group ----------
echo "[6/9] CloudWatch log group: ${LOG_GROUP}"
if ! aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" --region "$AWS_REGION" \
     | jq -e --arg lg "$LOG_GROUP" '.logGroups[]?.logGroupName == $lg' >/dev/null; then
  aws logs create-log-group --log-group-name "$LOG_GROUP" --region "$AWS_REGION" >/dev/null
  aws logs put-retention-policy --log-group-name "$LOG_GROUP" --retention-in-days 30 --region "$AWS_REGION" >/dev/null
  echo "  -> created (30d retention)"
else
  echo "  -> exists, skip"
fi

# ---------- 7. Batch Compute Env / Queue / Job Def ----------
echo "[7/9] Batch resources..."

# Compute Environment
render_json "${INFRA_DIR}/batch/compute-environment.json" "${TMP_DIR}/ce.json"
# subnet/SG/serviceRole 동적 주입
jq \
  --argjson subnets "$subnets_json" \
  --argjson sgs "$sgs_json" \
  --arg svc "arn:aws:iam::${AWS_ACCOUNT_ID}:role/aws-service-role/batch.amazonaws.com/AWSServiceRoleForBatch" \
  '.computeResources.subnets = $subnets
   | .computeResources.securityGroupIds = $sgs
   | .serviceRole = $svc' \
  "${TMP_DIR}/ce.json" > "${TMP_DIR}/ce.final.json"

CE_STATUS=$(aws batch describe-compute-environments \
  --compute-environments "$COMPUTE_ENV" --region "$AWS_REGION" \
  --query 'computeEnvironments[0].status' --output text 2>/dev/null || echo "NONE")
if [[ "$CE_STATUS" == "NONE" || "$CE_STATUS" == "None" ]]; then
  aws batch create-compute-environment --cli-input-json "file://${TMP_DIR}/ce.final.json" --region "$AWS_REGION" >/dev/null
  echo "  Compute Env: created"
else
  echo "  Compute Env: exists (${CE_STATUS}), skip update"
fi

# Wait until VALID
echo "  -> Compute Env VALID 대기..."
for _ in {1..30}; do
  s=$(aws batch describe-compute-environments --compute-environments "$COMPUTE_ENV" \
        --region "$AWS_REGION" --query 'computeEnvironments[0].status' --output text)
  [[ "$s" == "VALID" ]] && break
  sleep 5
done

# Job Queue
render_json "${INFRA_DIR}/batch/job-queue.json" "${TMP_DIR}/jq.json"
JQ_STATUS=$(aws batch describe-job-queues --job-queues "$JOB_QUEUE" --region "$AWS_REGION" \
  --query 'jobQueues[0].status' --output text 2>/dev/null || echo "NONE")
if [[ "$JQ_STATUS" == "NONE" || "$JQ_STATUS" == "None" ]]; then
  aws batch create-job-queue --cli-input-json "file://${TMP_DIR}/jq.json" --region "$AWS_REGION" >/dev/null
  echo "  Job Queue: created"
else
  echo "  Job Queue: exists, skip"
fi

# Job Definition
render_json "${INFRA_DIR}/batch/job-definition.json" "${TMP_DIR}/jd.json"
# image / role ARN 주입 (sed로 이미 account 치환됨 → image 태그 갱신만)
jq --arg img "${ECR_URI}:${IMAGE_TAG}" \
   '.containerProperties.image = $img' \
   "${TMP_DIR}/jd.json" > "${TMP_DIR}/jd.final.json"
aws batch register-job-definition --cli-input-json "file://${TMP_DIR}/jd.final.json" --region "$AWS_REGION" >/dev/null
echo "  Job Definition: registered (new revision)"

# ---------- 8. EventBridge Rule + DLQ + Target ----------
echo "[8/9] EventBridge + DLQ..."

# SQS DLQ
DLQ_URL=$(aws sqs get-queue-url --queue-name "$DLQ_NAME" --region "$AWS_REGION" \
  --query 'QueueUrl' --output text 2>/dev/null || echo "")
if [[ -z "$DLQ_URL" ]]; then
  DLQ_URL=$(aws sqs create-queue --queue-name "$DLQ_NAME" --region "$AWS_REGION" \
    --attributes "MessageRetentionPeriod=1209600" \
    --query 'QueueUrl' --output text)
  echo "  DLQ: created"
else
  echo "  DLQ: exists, skip"
fi
DLQ_ARN=$(aws sqs get-queue-attributes --queue-url "$DLQ_URL" --attribute-names QueueArn \
  --region "$AWS_REGION" --query 'Attributes.QueueArn' --output text)

# DLQ에 EventBridge SendMessage 허용 policy
DLQ_POLICY=$(jq -n --arg arn "$DLQ_ARN" --arg acct "$AWS_ACCOUNT_ID" '{
  Version:"2012-10-17",
  Statement:[{
    Effect:"Allow",
    Principal:{Service:"events.amazonaws.com"},
    Action:"sqs:SendMessage",
    Resource:$arn,
    Condition:{StringEquals:{"aws:SourceAccount":$acct}}
  }]
}')
aws sqs set-queue-attributes --queue-url "$DLQ_URL" \
  --attributes "Policy=${DLQ_POLICY}" --region "$AWS_REGION" >/dev/null

# Rule
render_json "${INFRA_DIR}/eventbridge/rule.json" "${TMP_DIR}/rule.json"
aws events put-rule --cli-input-json "file://${TMP_DIR}/rule.json" --region "$AWS_REGION" >/dev/null
echo "  Rule: put"

# Target
render_json "${INFRA_DIR}/eventbridge/target.json" "${TMP_DIR}/target.json"
aws events put-targets --cli-input-json "file://${TMP_DIR}/target.json" --region "$AWS_REGION" >/dev/null
echo "  Target: put"

# ---------- 9. SNS topic + Alarm ----------
echo "[9/9] SNS topic + CloudWatch Alarm..."
SNS_ARN=$(aws sns list-topics --region "$AWS_REGION" \
  --query "Topics[?ends_with(TopicArn, ':${SNS_TOPIC}')].TopicArn | [0]" --output text)
if [[ -z "$SNS_ARN" || "$SNS_ARN" == "None" ]]; then
  SNS_ARN=$(aws sns create-topic --name "$SNS_TOPIC" --region "$AWS_REGION" \
    --tags Key=Project,Value=gofactory-v3 Key=ManagedBy,Value=deploy.sh \
    --query 'TopicArn' --output text)
  echo "  SNS: created ($SNS_ARN)"
else
  echo "  SNS: exists ($SNS_ARN)"
fi

# email subscription (이미 있어도 idempotent)
EXISTING_SUB=$(aws sns list-subscriptions-by-topic --topic-arn "$SNS_ARN" --region "$AWS_REGION" \
  --query "Subscriptions[?Endpoint=='${ALERT_EMAIL}'].SubscriptionArn | [0]" --output text)
if [[ -z "$EXISTING_SUB" || "$EXISTING_SUB" == "None" || "$EXISTING_SUB" == "PendingConfirmation" ]]; then
  aws sns subscribe --topic-arn "$SNS_ARN" --protocol email \
    --notification-endpoint "$ALERT_EMAIL" --region "$AWS_REGION" >/dev/null
  echo "  SNS: email subscription requested -> 메일에서 'Confirm subscription' 클릭 필요"
else
  echo "  SNS: subscription exists"
fi

# CloudWatch Alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "gofactory-crawler-job-failures-7d" \
  --alarm-description "최근 7일 내 Batch 크롤러 잡 실패 1회 이상" \
  --metric-name FailedJobs \
  --namespace AWS/Batch \
  --statistic Sum \
  --period 604800 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching \
  --dimensions "Name=JobQueue,Value=${JOB_QUEUE}" \
  --alarm-actions "$SNS_ARN" \
  --region "$AWS_REGION" >/dev/null
echo "  Alarm: put"

# ---------- 완료 ----------
cat <<EOF

================================================================
  배포 완료
================================================================
  ECR Image:       ${ECR_URI}:${IMAGE_TAG}
  Compute Env:     ${COMPUTE_ENV}
  Job Queue:       ${JOB_QUEUE}
  Job Definition:  ${JOB_DEFINITION}
  Rule:            ${EVENT_RULE} (cron(0 17 ? * SAT *))
  SNS Topic:       ${SNS_ARN}
  Secret:          ${SECRET_ARN}

  테스트 트리거:
    aws batch submit-job \\
      --job-name gofactory-crawler-manual-test \\
      --job-queue ${JOB_QUEUE} \\
      --job-definition ${JOB_DEFINITION} \\
      --region ${AWS_REGION}

  로그 확인:
    aws logs tail ${LOG_GROUP} --follow --region ${AWS_REGION}
================================================================
EOF
