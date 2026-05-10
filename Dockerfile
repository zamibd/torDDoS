FROM golang:latest AS builder

WORKDIR /app
COPY api/go.mod api/go.sum ./
RUN go mod download

COPY api/ ./
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o torddos-api .

# ─────────────────────────────────────────────────────────────────────────────
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    tor \
    python3 \
    python3-venv \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Explicit SocksPort + Control Port (no cookie auth — unauthenticated NEWNYM)
RUN printf 'SocksPort 9050\nControlPort 9051\nCookieAuthentication 0\n' \
    >> /etc/tor/torrc

WORKDIR /app

# ── Mock sudo: strip "sudo -u <user>" prefix, then exec the rest ─────────────
RUN printf '#!/bin/sh\nif [ "$1" = "-u" ]; then shift 2; fi\nexec "$@"\n' \
    > /usr/local/bin/sudo && chmod +x /usr/local/bin/sudo

# ── Mock systemctl: delegate to /etc/init.d/tor ──────────────────────────────
RUN printf '#!/bin/sh\ncase "$1" in\n  is-active) pgrep -x tor >/dev/null; exit $? ;;\n  start)     /etc/init.d/tor start ;;\n  restart)   /etc/init.d/tor restart ;;\n  stop)      /etc/init.d/tor stop ;;\nesac\n' \
    > /usr/local/bin/systemctl && chmod +x /usr/local/bin/systemctl

COPY torddos.py requirements.txt ./
COPY lib/ ./lib/
COPY public/ ./public/

RUN python3 -m venv venv && \
    ./venv/bin/pip install --no-cache-dir --upgrade pip && \
    ./venv/bin/pip install --no-cache-dir -r requirements.txt

COPY --from=builder /app/torddos-api /usr/local/bin/

# Copy entrypoint as a real file — avoids echo/quoting hell
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8080

ENV TORDDOS_DIR=/app
ENV PORT=8080

ENTRYPOINT ["/app/entrypoint.sh"]
