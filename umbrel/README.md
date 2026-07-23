# MinerSentinel — Umbrel App

This directory is the [Umbrel](https://umbrel.com/) App Store package for MinerSentinel.

## App structure

```
umbrel/
├── docker-compose.yml    # Umbrel-compatible service definitions + image digests
├── umbrel-app.yml        # App manifest (id, port, tagline, gallery, …)
└── data/                 # Persistent data (created/managed by Umbrel)
```

App metadata highlights (see `umbrel-app.yml`):

| Field | Value |
|-------|--------|
| App id | `miner-sentinel` |
| UI port | `3080` |
| Category | `bitcoin` |
| Default username | `admin` |
| Password | Deterministic Umbrel app password (`deterministicPassword: true`) |

## Architecture on Umbrel

Four services (plus Umbrel `app_proxy`):

| Service | Image / role |
|---------|----------------|
| **db** | PostgreSQL 17 — persistent volume under `${APP_DATA_DIR}/data/db` |
| **backend** | Django REST API (Gunicorn), migrations + superuser bootstrap |
| **frontend** | React SPA via nginx |
| **data-service** | Collectors for Bitaxe, Avalon, CKPool/Public Pool; Telegram/Discord alerts |

Services run under non-root conventions where the stack defines them (e.g. Postgres `user: "1000:1000"`).

## Prerequisites before publishing

### 1. Multi-architecture images

Build and push `linux/arm64` and `linux/amd64` images (GitHub Container Registry, Docker Hub, etc.). Example tags used by this package:

```bash
# Enable Docker buildx
docker buildx create --use

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

The repo also includes `build_and_push_for_umbrel.sh` and `.github/workflows/build-and-push-umbrel.yml` for automated image updates.

### 2. Pin digests in `docker-compose.yml`

```bash
docker buildx imagetools inspect dcbert/minersentinel-backend:v1.0.0 --format '{{json .Manifest}}' | jq -r '.digest'
docker buildx imagetools inspect dcbert/minersentinel-frontend:v1.0.0 --format '{{json .Manifest}}' | jq -r '.digest'
docker buildx imagetools inspect dcbert/minersentinel-data-service:v1.0.0 --format '{{json .Manifest}}' | jq -r '.digest'
```

Reference images with digests:

```yaml
image: dcbert/minersentinel-backend:v1.0.0@sha256:<digest>
```

### 3. Assets for the App Store

- **Icon**: 256×256 SVG (no rounded corners — Umbrel applies rounding)
- **Gallery**: 3–5 screenshots, typically 1440×900 PNG (repo screenshots live under `docs/images/`)

## Testing on Umbrel

### Local development (OrbStack on macOS)

1. Install [OrbStack](https://orbstack.dev/)
2. Clone [getumbrel/umbrel](https://github.com/getumbrel/umbrel) and run `npm run dev`
3. Sync this package into a local app store path, for example:

```bash
rsync -av --exclude=".gitkeep" ./umbrel/ \
  umbrel@umbrel-dev.local:/home/umbrel/umbrel/app-stores/getumbrel-umbrel-apps-github-53f74447/miner-sentinel/
```

4. Install via UI or CLI:

```bash
npm run dev client -- apps.install.mutate -- --appId miner-sentinel
```

### Physical Umbrel device

```bash
rsync -av --exclude=".gitkeep" ./umbrel/ \
  umbrel@umbrel.local:/home/umbrel/umbrel/app-stores/getumbrel-umbrel-apps-github-53f74447/miner-sentinel/
```

```bash
umbreld client apps.install.mutate --appId miner-sentinel
```

## Initial setup after installation

1. Open the app (e.g. `http://umbrel.local:3080` or via the Umbrel UI).
2. Log in with username **`admin`** and the password shown by Umbrel for this app (deterministic app password).
3. The backend container bootstraps the Django superuser from `DJANGO_SUPERUSER_*` env (username `admin`, password `$APP_PASSWORD`).
4. In **Settings**:
   - Add Bitaxe and Avalon devices (IP addresses)
   - Select CKPool or Public Pool and set your mining address
   - Optionally enable **Telegram** and/or **Discord** webhooks
   - Set energy rate/currency for cost analysis
5. Django Admin (if needed) is available behind the same app proxy once authenticated, typically at `/admin/` on the app URL.

If you must create a superuser manually:

```bash
docker exec -it miner-sentinel_backend_1 python manage.py createsuperuser
```

(Exact container name may vary slightly by Umbrel version; use `docker ps` to confirm.)

## Environment variables (Umbrel-provided)

| Variable | Description |
|----------|-------------|
| `${APP_DATA_DIR}` | Persistent data directory for the app |
| `${APP_SEED}` | Unique seed used for Django `DJANGO_SECRET_KEY` |
| `${APP_PASSWORD}` | Deterministic app password (superuser) |
| `${DEVICE_DOMAIN_NAME}` | Local domain (e.g. `umbrel.local`) |

CORS/CSRF trusted origins are set to the Umbrel domain on port 3080 (and Tailscale `*.ts.net` variants) in `docker-compose.yml`.

## Submitting to the Umbrel App Store

1. Fork [getumbrel/umbrel-apps](https://github.com/getumbrel/umbrel-apps)
2. Branch: `git checkout -b add-miner-sentinel` (or update an existing `miner-sentinel` entry)
3. Copy the contents of this `umbrel/` directory into `miner-sentinel/` in the fork
4. Add `icon.svg` and gallery images
5. Open a PR using the store’s submission template

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

See also the upstream submission reference in `umbrel-app.yml` (`submission` field).

## Related docs

- Root project documentation: [../README.md](../README.md)
- Local development compose: [../docker-compose.yml](../docker-compose.yml)
- Production-style compose: [../docker-compose.prod.yml](../docker-compose.prod.yml)
