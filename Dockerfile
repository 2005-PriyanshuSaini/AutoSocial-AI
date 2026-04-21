FROM python:3.11.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for psycopg2 + healthcheck curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Run as non-root
RUN addgroup --system app && adduser --system --ingroup app --home /app app \
  && chown -R app:app /app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

ENV WEB_CONCURRENCY=2 \
    GUNICORN_TIMEOUT=60 \
    GUNICORN_GRACEFUL_TIMEOUT=30

USER app

# Production default: gunicorn + uvicorn workers
CMD ["bash", "-lc", "exec gunicorn -k uvicorn.workers.UvicornWorker -w ${WEB_CONCURRENCY} -b 0.0.0.0:8000 --timeout ${GUNICORN_TIMEOUT} --graceful-timeout ${GUNICORN_GRACEFUL_TIMEOUT} main:app"]
