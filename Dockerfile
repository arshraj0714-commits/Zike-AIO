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

# --- Copy start.sh from repo root INTO /app/bot -------------
#  Must come AFTER the bot source so it isn't shadowed.
#  The Dockerfile WORKDIR is /app/bot, so `bash start.sh`
#  in CMD will resolve to /app/bot/start.sh.
COPY start.sh /app/bot/start.sh
RUN chmod +x /app/bot/start.sh

# --- Environment defaults -----------------------------------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    API_ENABLED=true \
    API_PORT=8080

# --- Railway injects $PORT; start.sh maps PORT -> API_PORT --
CMD ["bash", "start.sh"]
