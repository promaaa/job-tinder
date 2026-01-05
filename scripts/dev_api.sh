#!/usr/bin/env bash
set -euo pipefail
ROOT=${JOB_TINDER_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
export JOB_TINDER_ROOT="$ROOT"
PORT=${PORT:-8000}
APP="backend.api.app:app"
exec uvicorn "$APP" --reload --port "$PORT"
