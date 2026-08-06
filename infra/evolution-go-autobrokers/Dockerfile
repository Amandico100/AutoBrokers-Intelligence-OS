# syntax=docker/dockerfile:1.7

ARG UPSTREAM_COMMIT=9337afc47e10b86cc896a6f432240e40fee95dd1
ARG VERSION=0.7.2-autobrokers.4

FROM alpine:3.21 AS source
ARG UPSTREAM_COMMIT
RUN apk add --no-cache git
WORKDIR /src
RUN git init \
    && git remote add origin https://github.com/evolution-foundation/evolution-go.git \
    && git fetch --depth 1 origin "${UPSTREAM_COMMIT}" \
    && git checkout --detach FETCH_HEAD \
    && test "$(git rev-parse HEAD)" = "${UPSTREAM_COMMIT}"
COPY patches /patches
RUN set -eux; \
    for patch in /patches/*.patch; do \
      git apply --check "${patch}"; \
      git apply "${patch}"; \
    done
COPY VERSION /src/VERSION

FROM golang:1.25.0-alpine AS build
ARG VERSION
RUN apk add --no-cache git build-base libjpeg-turbo-dev libwebp-dev
WORKDIR /build
COPY --from=source /src/go.mod /src/go.sum ./
RUN go mod download
COPY --from=source /src/ ./
RUN CGO_ENABLED=1 go test \
      ./pkg/config \
      ./pkg/passkey/... \
      ./pkg/instance/service \
      ./pkg/whatsmeow/service \
      ./pkg/server/handler \
      ./pkg/sendMessage/... \
    && CGO_ENABLED=1 go build -trimpath -ldflags "-s -w -X main.version=${VERSION}" -o /out/server ./cmd/evolution-go

FROM alpine:3.21 AS final
ARG UPSTREAM_COMMIT
ARG VERSION
LABEL org.opencontainers.image.title="Evolution Go AutoBrokers" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${UPSTREAM_COMMIT}" \
      org.opencontainers.image.source="https://github.com/evolution-foundation/evolution-go"
RUN apk add --no-cache tzdata ffmpeg libjpeg-turbo libwebp poppler-utils wget \
    && addgroup -S evolution \
    && adduser -S -G evolution evolution \
    && mkdir -p /app/logs \
    && chown evolution:evolution /app/logs
WORKDIR /app
COPY --from=build --chown=evolution:evolution /out/server ./server
COPY --from=source --chown=evolution:evolution /src/manager/dist ./manager/dist
COPY --from=source --chown=evolution:evolution /src/VERSION ./VERSION
ENV TZ=America/Sao_Paulo \
    SERVER_PORT=8080 \
    EVOLUTION_GO_VERSION=${VERSION}
EXPOSE 8080
USER evolution
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget -q -O - http://127.0.0.1:8080/server/ok || exit 1
ENTRYPOINT ["/app/server"]
