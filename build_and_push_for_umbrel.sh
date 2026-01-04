#!/bin/bash

# MinerSentinel Umbrel Deployment Script
# Builds multi-arch images and updates Umbrel docker-compose with new hashes

set -e

# Configuration
DOCKER_HUB_USER="dcbert"
VERSION="${VERSION:-v1.0.0}"
IMAGES=("backend" "frontend" "data-service")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}MinerSentinel Umbrel Deployment${NC}"
echo -e "${GREEN}Version: ${VERSION}${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to build and push a single image
build_and_push() {
    local service=$1
    local dockerfile_path=$2
    local context_path=$3
    local image_name="${DOCKER_HUB_USER}/minersentinel-${service}"

    echo -e "\n${YELLOW}Building ${service}...${NC}"

    docker buildx build --platform linux/arm64,linux/amd64 \
        --tag "${image_name}:latest" \
        --tag "${image_name}:${VERSION}" \
        -f "${dockerfile_path}" "${context_path}" \
        --push

    echo -e "${GREEN}✓ ${service} built and pushed${NC}"
}

# Function to get image digest
get_digest() {
    local image=$1
    docker buildx imagetools inspect "${image}:latest" --format '{{json .Manifest.Digest}}' | tr -d '"'
}

# Function to update umbrel docker-compose with new hashes
update_umbrel_compose() {
    local compose_file="umbrel/docker-compose.yml"

    echo -e "\n${YELLOW}Fetching image digests...${NC}"

    # Get digests for each image
    BACKEND_DIGEST=$(get_digest "${DOCKER_HUB_USER}/minersentinel-backend")
    FRONTEND_DIGEST=$(get_digest "${DOCKER_HUB_USER}/minersentinel-frontend")
    DATA_SERVICE_DIGEST=$(get_digest "${DOCKER_HUB_USER}/minersentinel-data-service")

    echo "Backend digest: ${BACKEND_DIGEST}"
    echo "Frontend digest: ${FRONTEND_DIGEST}"
    echo "Data-service digest: ${DATA_SERVICE_DIGEST}"

    echo -e "\n${YELLOW}Updating ${compose_file}...${NC}"

    # Create backup
    cp "${compose_file}" "${compose_file}.bak"

    # Update backend image line
    sed -i '' "s|image: ${DOCKER_HUB_USER}/minersentinel-backend:.*@sha256:.*|image: ${DOCKER_HUB_USER}/minersentinel-backend:latest@${BACKEND_DIGEST}|" "${compose_file}"

    # Update frontend image line
    sed -i '' "s|image: ${DOCKER_HUB_USER}/minersentinel-frontend:.*@sha256:.*|image: ${DOCKER_HUB_USER}/minersentinel-frontend:latest@${FRONTEND_DIGEST}|" "${compose_file}"

    # Update data-service image line
    sed -i '' "s|image: ${DOCKER_HUB_USER}/minersentinel-data-service:.*@sha256:.*|image: ${DOCKER_HUB_USER}/minersentinel-data-service:latest@${DATA_SERVICE_DIGEST}|" "${compose_file}"

    echo -e "${GREEN}✓ Updated ${compose_file}${NC}"
    echo -e "${YELLOW}Backup saved to ${compose_file}.bak${NC}"
}

# Main execution
main() {
    echo -e "\n${YELLOW}Step 1: Building and pushing images${NC}"
    echo "----------------------------------------"

    # Build backend
    build_and_push "backend" "backend/Dockerfile" "./backend"

    # Build frontend
    build_and_push "frontend" "frontend/Dockerfile" "./frontend"

    # Build data-service
    build_and_push "data-service" "data-service/Dockerfile" "./data-service"

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
    echo -e "  1. Review changes: git diff umbrel/docker-compose.yml"
    echo -e "  2. Commit changes: git add -A && git commit -m 'Update Umbrel images to ${VERSION}'"
    echo -e "  3. Push to repo: git push"
}

# Parse arguments
case "${1:-all}" in
    build)
        echo "Building images only..."
        build_and_push "backend" "backend/Dockerfile" "./backend"
        build_and_push "frontend" "frontend/Dockerfile" "./frontend"
        build_and_push "data-service" "data-service/Dockerfile" "./data-service"
        ;;
    update)
        echo "Updating Umbrel compose only..."
        update_umbrel_compose
        ;;
    backend|frontend|data-service)
        echo "Building ${1} only..."
        build_and_push "${1}" "${1}/Dockerfile" "./${1}"
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
        echo "  VERSION        - Image version tag (default: v1.0.0)"
        exit 1
        ;;
esac
