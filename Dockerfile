FROM node:24-slim AS frontend-build

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./
RUN npm run build

FROM python:3.12-alpine3.23@sha256:31a768b01976652c222e318fe5bd6e7c252f056cbf489c88fa256f1bf0af58e3 AS runtime

ARG BUILD_REVISION=unknown
LABEL org.opencontainers.image.revision=$BUILD_REVISION

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY --from=frontend-build /frontend/dist ./src/staylong/api/static

RUN python -m pip install --no-cache-dir '.[agents]' \
    && adduser -D -u 10001 -s /sbin/nologin staylong

USER 10001

EXPOSE 8080

CMD ["sh", "-c", "exec granian --interface asgi --http 1 --host 0.0.0.0 --port ${PORT} staylong.api.main:app"]
