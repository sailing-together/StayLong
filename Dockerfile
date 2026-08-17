FROM node:24-slim AS frontend-build

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY --from=frontend-build /frontend/dist ./src/staylong/api/static

RUN python -m pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin staylong

USER 10001

EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn staylong.api.main:app --host 0.0.0.0 --port ${PORT}"]
