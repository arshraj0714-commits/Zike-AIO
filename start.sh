#!/usr/bin/env bash
# =============================================================
#  Zike Bot — Railway launcher (BOT ONLY)
# =============================================================
#  Used by Dockerfile CMD. The Docker image is built from
#  python:3.11-slim, so `python` is on $PATH at /usr/local/bin.
#  No venv detection needed — the whole container IS the env.
# =============================================================
set -euo pipefail

# --- Map Railway's $PORT to the bot's API_PORT ---------------
export API_PORT="${PORT:-8080}"
export API_ENABLED="${API_ENABLED:-true}"

# --- Sanity check -------------------------------------------
if ! command -v python >/dev/null 2>&1; then
  echo "FATAL: python not on PATH"
  echo "PATH=$PATH"
  exit 1
fi

cd /app/bot

echo "════════════════════════════════════════"
echo "  Zike Bot — Railway launcher"
echo "  PORT     = ${PORT:-8080}    (Railway public ingress)"
echo "  API_PORT = ${API_PORT}    (FastAPI listens here)"
echo "  Python   = $(which python)  ($(python --version))"
echo "  CWD      = $(pwd)"
echo "════════════════════════════════════════"

# --- Launch the bot (replaces this shell, becomes PID 1) -----
exec python Zike.py
