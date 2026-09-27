#!/bin/bash

# MinerSentinel Umbrel Deployment Script
# Builds multi-arch images and updates Umbrel docker-compose with new hashes

set -euo pipefail

# Configuration
DOCKER_HUB_USER="${DOCKER_HUB_USER:-dcbert}"
VERSION="${VERSION:-v1.1.1}"
COMPOSE_FILE="umbrel/docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}MinerSentinel Umbrel Deployment${NC}"
echo -e "${GREEN}Version: ${VERSION}${NC}"
echo -e "${GREEN}========================================${NC}"

# Detect sed in-place flag (GNU vs BSD)
if sed --version >/dev/null 2>&1; then
  SED_INPLACE=(sed -i)
else
  SED_INPLACE=(sed -i '')
fi

build_and_push() {
    local service=$1
    local image_name="${DOCKER_HUB_USER}/minersentinel-${service}"

    echo -e "\n${YELLOW}Building ${service}...${NC}"

    docker buildx build --platform linux/arm64,linux/amd64 \
        --tag "${image_name}:latest" \
        --tag "${image_name}:${VERSION}" \
        -f "${service}/Dockerfile" "./${service}" \
        --push

    echo -e "${GREEN}✓ ${service} built and pushed${NC}"
}

get_digest() {
    local image=$1
    local tag=$2
    docker buildx imagetools inspect "${image}:${tag}" --format '{{json .Manifest}}' \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["digest"])'
}

update_umbrel_compose() {
    echo -e "\n${YELLOW}Fetching image digests for ${VERSION}...${NC}"

    BACKEND_DIGEST=$(get_digest "${DOCKER_HUB_USER}/minersentinel-backend" "${VERSION}")
    FRONTEND_DIGEST=$(get_digest "${DOCKER_HUB_USER}/minersentinel-frontend" "${VERSION}")
    DATA_SERVICE_DIGEST=$(get_digest "${DOCKER_HUB_USER}/minersentinel-data-service" "${VERSION}")

    echo "Backend digest: ${BACKEND_DIGEST}"
    echo "Frontend digest: ${FRONTEND_DIGEST}"
    echo "Data-service digest: ${DATA_SERVICE_DIGEST}"

    echo -e "\n${YELLOW}Updating ${COMPOSE_FILE}...${NC}"

    cp "${COMPOSE_FILE}" "${COMPOSE_FILE}.bak"

    python3 - << PYEOF
import re
from pathlib import Path

user = "${DOCKER_HUB_USER}"
version = "${VERSION}"
backend = "${BACKEND_DIGEST}"
frontend = "${FRONTEND_DIGEST}"
data = "${DATA_SERVICE_DIGEST}"
path = Path("${COMPOSE_FILE}")
content = path.read_text()

replacements = {
    f"{user}/minersentinel-backend": f"{user}/minersentinel-backend:{version}@{backend}",
    f"{user}/minersentinel-frontend": f"{user}/minersentinel-frontend:{version}@{frontend}",
    f"{user}/minersentinel-data-service": f"{user}/minersentinel-data-service:{version}@{data}",
}

for prefix, replacement in replacements.items():
    content = re.sub(
        rf"image:\s*{re.escape(prefix)}:[^\s]+",
        f"image: {replacement}",
        content,
    )

path.write_text(content)
print("✓ compose updated")
PYEOF

    echo -e "${GREEN}✓ Updated ${COMPOSE_FILE}${NC}"
    echo -e "${YELLOW}Backup saved to ${COMPOSE_FILE}.bak${NC}"
}

main() {
    echo -e "\n${YELLOW}Step 1: Building and pushing images${NC}"
    echo "----------------------------------------"

    build_and_push "backend"
    build_and_push "frontend"
    build_and_push "data-service"

    echo -e "\n${YELLOW}Step 2: Updating Umbrel docker-compose${NC}"
    echo "----------------------------------------"

    update_umbrel_compose

    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ Deployment complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "\nNew image digests:"
    echo -e "  Backend:      ${BACKEND_DIGEST}"
    echo -e "  Frontend:     ${FRONTEND_DIGEST}"
    echo -e "  Data-service: ${DATA_SERVICE_DIGEST}"
    echo -e "\nNext steps:"
    echo -e "  1. Confirm umbrel/umbrel-app.yml version matches ${VERSION#v}"
    echo -e "  2. Review: git diff umbrel/"
    echo -e "  3. Commit, then PR the umbrel/ contents into getumbrel/umbrel-apps/miner-sentinel/"
}

case "${1:-all}" in
    build)
        build_and_push "backend"
        build_and_push "frontend"
        build_and_push "data-service"
        ;;
    update)
        update_umbrel_compose
        ;;
    backend|frontend|data-service)
        build_and_push "${1}"
        ;;
    all|"")
        main
        ;;
    *)
        echo "Usage: $0 [all|build|update|backend|frontend|data-service]"
        echo ""
        echo "Commands:"
        echo "  all (default)  - Build all images and update Umbrel compose"
        echo "  build          - Build and push all images only"
        echo "  update         - Update Umbrel compose with current digests only"
        echo "  backend        - Build backend only"
        echo "  frontend       - Build frontend only"
        echo "  data-service   - Build data-service only"
        echo ""
        echo "Environment variables:"
        echo "  VERSION          - Image version tag (default: v1.1.1)"
        echo "  DOCKER_HUB_USER  - Docker Hub namespace (default: dcbert)"
        exit 1
        ;;
esac
