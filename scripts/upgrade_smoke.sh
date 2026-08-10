#!/usr/bin/env bash
# Upgrade simulation for device unification Release C.
# Prefer Postgres (production path). SQLite cannot run early RunSQL defaults.
#
# Usage (with docker-compose Postgres already running):
#   export DATABASE_URL=postgresql://minersentinel:minersentinel@localhost:5432/minersentinel
#   ./scripts/upgrade_smoke.sh
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

echo "==> Apply migrations through latest (includes 0011–0014)"
python manage.py migrate --noinput

echo "==> Verify unified registry (Release C: legacy tables gone)"
python manage.py verify_device_unification --registry-only

echo "==> Verify unification report"
python manage.py verify_device_unification || true

echo "==> Upgrade smoke complete"
