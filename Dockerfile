# =============================================================
#  Dockerfile · Zike Bot (Railway, BOT ONLY)
# =============================================================
#  Railway auto-detects this Dockerfile and uses it INSTEAD of
#  Railpack — no detection magic, fully deterministic.
#
#  The Next.js dashboard deploys separately on Vercel
#  (see vercel.json in the repo root).
# =============================================================

FROM python:3.11-slim

# --- System packages ----------------------------------------
#  ffmpeg       → discord voice / wavelink playback
#  libffi-dev   → cffi / cryptography wheels
#  libsndfile1  → audio I/O
#  fonts-noto   → PIL image rendering (welcome cards)
#  curl         → healthchecks / tunnel debug
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg \
      libffi-dev \
      libsndfile1 \
      fonts-noto-core \
      fonts-noto-cjk \
      fontconfig \
      curl \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# --- Working directory --------------------------------------
WORKDIR /app/bot

# --- Install Python deps FIRST (better layer caching) -------
#  Copy only requirements.txt so dependency changes don't
#  invalidate the cache for the rest of the source.
COPY bot/requirements.txt /app/bot/requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

# --- Copy the rest of the bot source ------------------------
COPY bot /app/bot

# --- Environment defaults -----------------------------------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    API_ENABLED=true \
    API_PORT=8080

# --- Railway injects $PORT; map it to API_PORT --------------
#  start.sh handles the PORT -> API_PORT mapping.
CMD ["bash", "start.sh"]
