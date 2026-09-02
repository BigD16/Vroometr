# Python image for the API and the Celery worker.
# Same filesystem; Compose/deploy choose the command at runtime.
#
#   docker build -f infra/docker/python.Dockerfile -t vroometr-python .
#
# Do not put passwords, ports, or hosts in this file. Pass them as env at run time.

FROM python:3.12-slim-bookworm

WORKDIR /app

COPY pyproject.toml README.md ./
COPY libs ./libs
COPY services ./services
COPY pipelines ./pipelines
COPY workers ./workers

RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app/libs:/app/services/api:/app

WORKDIR /app/services/api

# API is the default process. Worker: celery -A workers.celery_app worker
CMD ["sh", "-c", "exec uvicorn app.main:app --host \"$API_HOST\" --port \"$API_PORT\""]
