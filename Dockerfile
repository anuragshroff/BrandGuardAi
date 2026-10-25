# syntax=docker/dockerfile:1

# ---- Stage 1: build the Next.js static export -----------------------------
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# "/" = same origin, served by FastAPI below (Next drops empty env vars).
ENV NEXT_STATIC_EXPORT=1
ENV NEXT_PUBLIC_API_URL="/"
RUN npm run build

# ---- Stage 2: FastAPI + bundled frontend ----------------------------------
FROM python:3.12-slim AS api
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY --from=web /web/out ./static
RUN mkdir -p /app/data

ENV FRONTEND_DIST=/app/static \
    BRANDGUARD_DB=/app/data/brandguard.db \
    BRANDGUARD_SEED_DEMO=1

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
