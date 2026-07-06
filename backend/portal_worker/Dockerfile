# SPEC-020 P1 — portal-worker: Playwright (chromium headless já incluso na base)
# + FastAPI fino. EasyPanel: build context = RAIZ do repo; Dockerfile path =
# backend/portal_worker/Dockerfile.
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY backend/portal_worker/requirements.txt /app/portal_worker/requirements.txt
RUN pip install --no-cache-dir -r /app/portal_worker/requirements.txt

COPY backend/portal_worker /app/portal_worker

EXPOSE 8080
CMD ["uvicorn", "portal_worker.main:app", "--host", "0.0.0.0", "--port", "8080"]
