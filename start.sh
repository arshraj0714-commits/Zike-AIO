#!/usr/bin/env bash
# =============================================================
#  Zike Bot — Railway launcher (BOT ONLY)
# =============================================================
#  Railpack installs Python into /opt/venv (created in the
#  install phase of railpack.toml). System python3 is NOT on
#  $PATH, so we MUST use the venv interpreter explicitly.
#
#  Railway exposes the public ingress via $PORT. The bot's
#  FastAPI (uvicorn) listens on $API_PORT — we map them so
#  the Railway public URL routes directly to the bot's API.
#
#  The Next.js dashboard is deployed separately on Vercel
#  (see vercel.json in the repo root).
# =============================================================
set -euo pipefail

# --- Map Railway's $PORT to the bot's API_PORT ---------------
export API_PORT="${PORT:-8080}"
export API_ENABLED="${API_ENABLED:-true}"

# --- Pick the Python interpreter (venv FIRST, always) --------
#  Railpack puts Python ONLY in /opt/venv — never on $PATH.
PYTHON_BIN="/opt/venv/bin/python"

#  Belt-and-suspenders: also expose the venv on $PATH in case
#  bot/Zike.py shells out to `python3` or `pip` somewhere.
export PATH="/opt/venv/bin:${PATH}"

#  Sanity check — fail fast with a useful message instead of
#  the cryptic "exec: python3: not found" loop.
if [ ! -x "$PYTHON_BIN" ]; then
  echo "══════════════════════════════════════════════════════"
  echo "  FATAL: $PYTHON_BIN not found."
  echo "  Did the railpack.toml install phase run?"
  echo "  Contents of /opt/venv/bin:"
  ls -la /opt/venv/bin 2>&1 || echo "  (no /opt/venv at all)"
  echo "══════════════════════════════════════════════════════"
  exit 1
fi

cd /app/bot

echo "════════════════════════════════════════"
echo "  Zike Bot — Railway launcher"
echo "  PORT     = ${PORT:-8080}    (Railway public ingress)"
echo "  API_PORT = ${API_PORT}    (FastAPI listens here)"
echo "  Python   = ${PYTHON_BIN}  ($(${PYTHON_BIN} --version))"
echo "  CWD      = $(pwd)"
echo "════════════════════════════════════════"

# --- Launch the bot (replaces this shell, becomes PID 1) -----
#  Railway sends SIGTERM here on redeploy; Python handles it.
exec "$PYTHON_BIN" Zike.py
