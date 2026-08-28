FROM node:24-slim AS frontend-build

WORKDIR /frontend

ARG VITE_STAYLONG_API_MODE
ENV VITE_STAYLONG_API_MODE=$VITE_STAYLONG_API_MODE

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./
RUN npm run build

FROM python:3.12-alpine3.24@sha256:d09d15e60962ca365d1cd544a48773bac9d33f2fb1b00f2aa0deec78ade7dc31 AS runtime

ARG BUILD_REVISION=unknown
LABEL org.opencontainers.image.revision=$BUILD_REVISION

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY --from=frontend-build /frontend/dist ./src/staylong/api/static

RUN apk upgrade --no-cache \
    && python -m pip install --no-cache-dir '.[agents]' \
    && adduser -D -u 10001 -s /sbin/nologin staylong

USER 10001

EXPOSE 8080

CMD ["sh", "-c", "exec granian --interface asgi --http 1 --host 0.0.0.0 --port ${PORT} staylong.api.main:app"]
