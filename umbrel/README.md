# MinerSentinel — Umbrel App

This directory is the [Umbrel](https://umbrel.com/) App Store package for MinerSentinel.
The live store package lives in [getumbrel/umbrel-apps](https://github.com/getumbrel/umbrel-apps/tree/master/miner-sentinel)
(merged via [#4354](https://github.com/getumbrel/umbrel-apps/pull/4354)).

## App structure

```
umbrel/
├── docker-compose.yml    # Umbrel-compatible services + pinned image digests
├── umbrel-app.yml        # App manifest (id, port, tagline, gallery, …)
└── data/db/              # Postgres bind-mount source (`.gitkeep` stripped by Umbrel)
```

| Field | Value |
|-------|--------|
| App id | `miner-sentinel` |
| UI port | `3082` |
| Category | `bitcoin` |
| Default username | `admin` |
| Password | Deterministic Umbrel app password (`deterministicPassword: true`) |

## Architecture on Umbrel

Four services (plus Umbrel `app_proxy`):

| Service | Role |
|---------|------|
| **db** | PostgreSQL under `${APP_DATA_DIR}/data/db` |
| **backend** | Django REST API (Gunicorn), migrations + superuser bootstrap |
| **frontend** | React SPA via nginx (proxies `/api` to backend) |
| **data-service** | Multi-make collectors + Telegram/Discord alerts |

On install/upgrade the backend runs `python manage.py migrate`. Services that support it run as `user: "1000:1000"`.

## Before submitting an update to umbrel-apps

### 1. Build and push multi-arch images

Images must support `linux/amd64` and `linux/arm64`. Prefer the GitHub Action:

```bash
# In the GitHub UI: Actions → "Build & Push for Umbrel" → Run workflow
# Input version: v1.1.1
```

Or locally (Docker buildx + Docker Hub login required):

```bash
VERSION=v1.1.1 ./build_and_push_for_umbrel.sh
```

### 2. Confirm digests are pinned with version tags

Compose must use `repo:tag@sha256:…` (not bare `latest`). After the build script/Action runs, verify:

```bash
grep 'image: dcbert/minersentinel' umbrel/docker-compose.yml
```

Also bump `version` and `releaseNotes` in `umbrel-app.yml` to match the images.

### 3. Copy into a fork of umbrel-apps

```bash
# From a clone of your umbrel-apps fork:
rsync -av --delete \
  --exclude README.md \
  --exclude '.gitkeep' \
  ./umbrel/ \
  /path/to/umbrel-apps/miner-sentinel/
```

Do **not** commit screenshots or an `icon` for official App Store PRs; Umbrel hosts those assets.
Keep the existing `gallery:` filenames from the store package.

Open a PR against `getumbrel/umbrel-apps` describing the version bump and testing performed.

## Testing on Umbrel

### Local development (OrbStack on macOS)

1. Install [OrbStack](https://orbstack.dev/)
2. Clone [getumbrel/umbrel](https://github.com/getumbrel/umbrel) and run `npm run dev`
3. Sync this package into the local app store path, for example:

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

1. Open the app (e.g. `http://umbrel.local:3082` or via the Umbrel UI).
2. Log in with username **`admin`** and the password Umbrel shows for this app.
3. In **Settings**:
   - **Devices** — add miners (make + IP)
   - **Data Collector** — CKPool, Public Pool, or BTC PoW Lab
   - **Notifications** — optional Telegram and/or Discord
   - Energy rate/currency for cost analysis
4. Django Admin is available at `/admin/` on the app URL once authenticated.

## Environment variables (Umbrel-provided)

| Variable | Description |
|----------|-------------|
| `${APP_DATA_DIR}` | Persistent data directory for the app |
| `${APP_SEED}` | Mapped to Django `SECRET_KEY` |
| `${APP_PASSWORD}` | Deterministic app password (superuser) |
| `${DEVICE_DOMAIN_NAME}` | Local domain (e.g. `umbrel.local`) |
| `${APP_PROXY_PORT}` | Host port from the manifest (`3082`) |

## Related docs

- Root project documentation: [../README.md](../README.md)
- Local development compose: [../docker-compose.yml](../docker-compose.yml)
- Production-style compose: [../docker-compose.prod.yml](../docker-compose.prod.yml)
