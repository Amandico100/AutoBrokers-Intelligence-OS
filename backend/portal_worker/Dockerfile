# SPEC-020 P1 — portal-worker: Playwright (chromium headless já incluso na base)
# + FastAPI fino. EasyPanel: build context = RAIZ do repo; Dockerfile path =
# backend/portal_worker/Dockerfile.

# Stage gitinfo: extrai o commit SHA do contexto de build (sem exigir git no
# runtime) — o /health expõe build_sha/build_time p/ provar a versão no ar.
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy AS gitinfo
WORKDIR /ctx
COPY . .
RUN sh -c 'SHA=""; HEAD=$(cat .git/HEAD 2>/dev/null || true); \
    case "$HEAD" in \
      ref:*) REF=$(echo "$HEAD" | cut -d" " -f2); \
             SHA=$(cat ".git/$REF" 2>/dev/null || true); \
             [ -n "$SHA" ] || SHA=$(grep " $REF" .git/packed-refs 2>/dev/null | head -1 | cut -d" " -f1);; \
      *) SHA="$HEAD";; \
    esac; \
    echo "${SHA:-unknown}" | cut -c1-12 > /build_sha.txt; \
    date -u +%Y-%m-%dT%H:%M:%SZ > /build_time.txt; \
    echo "build_sha=$(cat /build_sha.txt) build_time=$(cat /build_time.txt)"'

FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY backend/portal_worker/requirements.txt /app/portal_worker/requirements.txt
RUN pip install --no-cache-dir -r /app/portal_worker/requirements.txt

COPY backend/portal_worker /app/portal_worker
COPY --from=gitinfo /build_sha.txt /app/portal_worker/build_sha.txt
COPY --from=gitinfo /build_time.txt /app/portal_worker/build_time.txt

EXPOSE 8080
CMD ["uvicorn", "portal_worker.main:app", "--host", "0.0.0.0", "--port", "8080"]
