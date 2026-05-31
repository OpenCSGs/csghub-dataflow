#!/usr/bin/env bash
# Build and push Argo full operator image
# Usage: ./scripts/build-push-argo.sh [registry] [tag]

set -euo pipefail

REGISTRY="${1:-192.168.2.98:8140}"
TAG="${2:-argo-latest}"
IMAGE="${REGISTRY}/opencsg_public/dataflow:${TAG}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

export DOCKER_BUILDKIT=1

echo "==> build ${IMAGE} (full operator deps: docker/dataflow_requirements.txt)"
docker build \
  -f "${ROOT}/Dockerfile-argo" \
  --build-arg BUILD_CN=true \
  --build-arg PRELOAD_ASSETS="${PRELOAD_ASSETS:-true}" \
  "${@:3}" \
  -t "${IMAGE}" \
  "${ROOT}"

echo "==> push ${IMAGE}"
docker push "${IMAGE}"

echo "==> done: ${IMAGE}"
