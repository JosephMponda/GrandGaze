# MUST-GSL EMR - Production-grade Docker image
# Multi-stage: build static assets, then slim runtime with non-root user
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Runtime stage ----
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Non-root user for security (P14)
RUN groupadd -r django && useradd -r -g django django

COPY --from=builder /root/.local /home/django/.local
ENV PATH=/home/django/.local/bin:$PATH
ENV PYTHONUSERBASE=/home/django/.local

COPY --chown=django:django . .

RUN python manage.py collectstatic --noinput --clear

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -sf http://localhost:8000/health/ || exit 1

EXPOSE 8000

USER django

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
