#!/usr/bin/env bash
# =============================================================
#  Zike Bot — Railway launcher (BOT ONLY)
# =============================================================
#  Railway exposes the public ingress via $PORT. The bot's
#  FastAPI (uvicorn) listens on $API_PORT — we map them so
#  the Railway public URL routes directly to the bot's API,
#  no Cloudflare tunnel needed (the tunnel still runs as a
#  backup URL, printed on first boot).
#
#  The Next.js dashboard is deployed separately on Vercel —
#  see vercel.json in the repo root.
# =============================================================
set -euo pipefail

# --- Map Railway's $PORT to the bot's API_PORT ---------------
export API_PORT="${PORT:-8000}"
export API_ENABLED="${API_ENABLED:-true}"

cd /app/bot

# --- Pick the right Python -----------------------------------
#  Use the venv created during install phase if it exists,
#  otherwise fall back to system python3.
PYTHON_BIN="/opt/venv/bin/python"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="python3"

echo "════════════════════════════════════════"
echo "  Zike Bot — Railway launcher"
echo "  PORT     = ${PORT:-3000}    (Railway public ingress)"
echo "  API_PORT = ${API_PORT}    (FastAPI listens here)"
echo "  Python   = ${PYTHON_BIN}"
echo "════════════════════════════════════════"

# --- Launch the bot (replaces this shell, becomes PID 1) -----
#  Railway sends SIGTERM here on redeploy; Python handles it.
exec "$PYTHON_BIN" Zike.py
