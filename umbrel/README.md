# MinerSentinel - Umbrel App

This directory contains the Umbrel App Store package for MinerSentinel.

## App Structure

```
umbrel/
├── docker-compose.yml    # Umbrel-compatible Docker Compose
├── umbrel-app.yml        # App manifest for Umbrel
├── exports.sh            # Environment exports
└── data/                 # Persistent data directory (created by Umbrel)
    └── .gitkeep
```

## Prerequisites

Before publishing to the Umbrel App Store, you need to:

1. **Build and push multi-architecture Docker images** to a public registry (GitHub Container Registry, Docker Hub, etc.):

```bash
# Enable Docker buildx
docker buildx create --use

# Build and push all images for linux/arm64 and linux/amd64
docker buildx build --platform linux/arm64,linux/amd64 \
  --tag dcbert/minersentinel-backend:latest \
  --tag dcbert/minersentinel-backend:v1.0.0 \
  -f backend/Dockerfile ./backend \
  --push

docker buildx build --platform linux/arm64,linux/amd64 \
  --tag dcbert/minersentinel-frontend:latest \
  --tag dcbert/minersentinel-frontend:v1.0.0 \
  -f frontend/Dockerfile ./frontend \
  --push

docker buildx build --platform linux/arm64,linux/amd64 \
  --tag dcbert/minersentinel-data-service:latest \
  --tag dcbert/minersentinel-data-service:v1.0.0 \
  -f data-service/Dockerfile ./data-service \
  --push
```

2. **Get image digests** and update `docker-compose.yml`:

```bash
# Get the multi-arch digest for each image
docker buildx imagetools inspect dcbert/minersentinel-backend:v1.0.0 --format '{{json .Manifest}}' | jq -r '.digest'
docker buildx imagetools inspect dcbert/minersentinel-frontend:v1.0.0 --format '{{json .Manifest}}' | jq -r '.digest'
docker buildx imagetools inspect dcbert/minersentinel-data-service:v1.0.0 --format '{{json .Manifest}}' | jq -r '.digest'
```

Then update the image references in `docker-compose.yml` to include the digest:
```yaml
image: dcbert/minersentinel-backend:v1.0.0@sha256:<digest>
```

3. **Create app icon**: Upload a 256x256 SVG icon (no rounded corners - Umbrel applies CSS rounding).

4. **Create gallery images**: Create 3-5 high-quality screenshots (1440x900px PNG format).

## Testing on Umbrel

### Local Development (with OrbStack on macOS)

1. Install [OrbStack](https://orbstack.dev/) on macOS
2. Clone the [getumbrel/umbrel](https://github.com/getumbrel/umbrel) repo
3. Start the development environment:
   ```bash
   cd umbrel
   npm run dev
   ```
4. Copy this app to the Umbrel app store:
   ```bash
   rsync -av --exclude=".gitkeep" ./umbrel/ \
     umbrel@umbrel-dev.local:/home/umbrel/umbrel/app-stores/getumbrel-umbrel-apps-github-53f74447/minersentinel/
   ```
5. Install via Umbrel UI or CLI:
   ```bash
   npm run dev client -- apps.install.mutate -- --appId minersentinel
   ```

### On Physical Umbrel Device

1. Copy app directory to your Umbrel:
   ```bash
   rsync -av --exclude=".gitkeep" ./umbrel/ \
     umbrel@umbrel.local:/home/umbrel/umbrel/app-stores/getumbrel-umbrel-apps-github-53f74447/minersentinel/
   ```
2. Install from the App Store or via terminal:
   ```bash
   umbreld client apps.install.mutate --appId minersentinel
   ```

## Initial Setup After Installation

1. Access the app at `http://umbrel.local:3080`
2. Create an admin user via Django admin:
   - SSH into your Umbrel: `ssh umbrel@umbrel.local`
   - Access the backend container:
     ```bash
     docker exec -it minersentinel_backend_1 python manage.py createsuperuser
     ```
3. Login to Django admin at `http://umbrel.local:3080/admin/` to:
   - Add Bitaxe and Avalon devices
   - Configure pool settings
   - Set up Telegram notifications

## Submitting to Umbrel App Store

1. Fork [getumbrel/umbrel-apps](https://github.com/getumbrel/umbrel-apps)
2. Create a new branch: `git checkout -b add-minersentinel`
3. Copy the `umbrel/` contents to `minersentinel/` in the forked repo
4. Add icon.svg and gallery images
5. Open a PR with the following template:

```markdown
# App Submission

### App name
MinerSentinel

### 256x256 SVG icon
[Upload icon]

### Gallery images
[Upload 3-5 screenshots at 1440x900px]

### I have tested my app on:
- [ ] umbrelOS on a Raspberry Pi
- [ ] umbrelOS on an Umbrel Home
- [ ] umbrelOS on Linux VM
```

## Environment Variables

The following Umbrel-provided variables are used:

| Variable | Description |
|----------|-------------|
| `${APP_DATA_DIR}` | Persistent data directory for the app |
| `${APP_SEED}` | Unique 256-bit hex string for secrets |
| `${DEVICE_DOMAIN_NAME}` | Local domain (e.g., `umbrel.local`) |

## Architecture

MinerSentinel consists of 4 services:

1. **postgres** - PostgreSQL 16 database for storing all data
2. **backend** - Django REST API server
3. **frontend** - React app served via nginx
4. **data-service** - Python service polling mining devices

All services run as non-root user (UID 1000) for security.
