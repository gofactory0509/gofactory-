#!/usr/bin/env bash
# =============================================================================
# 크롤러 이미지만 재빌드 + 재push + Job Definition revision 갱신
# =============================================================================
# 사용법:
#   export AWS_ACCOUNT_ID=... AWS_REGION=us-east-1
#   ./infra/redeploy-image.sh           # tag=latest
#   IMAGE_TAG=v1.2 ./infra/redeploy-image.sh
# =============================================================================

set -euo pipefail

REQUIRED_VARS=(AWS_ACCOUNT_ID AWS_REGION)
for v in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    echo "[ERROR] 환경변수 누락: $v" >&2
    exit 1
  fi
done

for cmd in aws docker jq; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[ERROR] 필수 도구 누락: $cmd" >&2
    exit 1
  fi
done

ECR_REPO="gofactory-crawler"
IMAGE_TAG="${IMAGE_TAG:-latest}"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"
JOB_DEFINITION="gofactory-crawler-job"

INFRA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${INFRA_DIR}/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "[1/3] Docker login + build + push (${IMAGE_TAG})..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com" >/dev/null
(cd "$REPO_ROOT" && docker build -t "${ECR_REPO}:${IMAGE_TAG}" .)
docker tag "${ECR_REPO}:${IMAGE_TAG}" "${ECR_URI}:${IMAGE_TAG}"
docker push "${ECR_URI}:${IMAGE_TAG}"
echo "  -> pushed ${ECR_URI}:${IMAGE_TAG}"

echo "[2/3] Job Definition revision 갱신..."
sed "s|REPLACE_WITH_ACCOUNT_ID|${AWS_ACCOUNT_ID}|g" \
  "${INFRA_DIR}/batch/job-definition.json" > "${TMP_DIR}/jd.json"
jq --arg img "${ECR_URI}:${IMAGE_TAG}" \
   '.containerProperties.image = $img' \
   "${TMP_DIR}/jd.json" > "${TMP_DIR}/jd.final.json"
REV_ARN=$(aws batch register-job-definition \
  --cli-input-json "file://${TMP_DIR}/jd.final.json" \
  --region "$AWS_REGION" \
  --query 'jobDefinitionArn' --output text)
echo "  -> new revision: $REV_ARN"

echo "[3/3] 완료. 다음 정기 실행부터 신규 revision 사용."
echo "  수동 테스트:"
echo "    aws batch submit-job \\"
echo "      --job-name gofactory-crawler-manual-\$(date +%s) \\"
echo "      --job-queue gofactory-crawler-queue \\"
echo "      --job-definition ${JOB_DEFINITION} \\"
echo "      --region ${AWS_REGION}"
