FROM golang:latest AS builder

WORKDIR /app
COPY api/go.mod api/go.sum ./
RUN go mod download

COPY api/ ./
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o torddos-api .

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    tor \
    python3 \
    python3-venv \
    procps \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

RUN echo "ControlPort 9051\nCookieAuthentication 0" >> /etc/tor/torrc

WORKDIR /app

# Mock sudo and systemctl for lib/tor.py
RUN echo '#!/bin/bash\n\
if [ "$1" == "-u" ]; then shift 2; fi\n\
exec "$@"' > /usr/local/bin/sudo && chmod +x /usr/local/bin/sudo

RUN echo '#!/bin/bash\n\
if [ "$1" = "is-active" ]; then\n\
    pgrep -x tor > /dev/null\n\
    exit $?\n\
elif [ "$1" = "start" ]; then\n\
    /etc/init.d/tor start\n\
elif [ "$1" = "restart" ]; then\n\
    /etc/init.d/tor restart\n\
elif [ "$1" = "stop" ]; then\n\
    /etc/init.d/tor stop\n\
fi' > /usr/local/bin/systemctl && chmod +x /usr/local/bin/systemctl

COPY torddos.py requirements.txt ./
COPY lib/ ./lib/
COPY public/ ./public/

RUN python3 -m venv venv && \
    ./venv/bin/pip install --no-cache-dir --upgrade pip && \
    ./venv/bin/pip install --no-cache-dir -r requirements.txt

COPY --from=builder /app/torddos-api /usr/local/bin/

EXPOSE 8080

ENV TORDDOS_DIR=/app
ENV PORT=8080

RUN echo '#!/bin/sh\n\
set -e\n\
echo "[entrypoint] Starting Tor daemon..."\n\
/etc/init.d/tor start || tor --defaults-torrc /usr/share/tor/tor-service-defaults-torrc -f /etc/tor/torrc --RunAsDaemon 1\n\
echo "[entrypoint] Waiting for Tor SOCKS5 port (9050)..."\n\
for i in $(seq 1 30); do\n\
    nc -z 127.0.0.1 9050 2>/dev/null \&\& break\n\
    echo "[entrypoint] Waiting... ($i/30)"\n\
    sleep 1\n\
done\n\
if ! nc -z 127.0.0.1 9050 2>/dev/null; then\n\
    echo "[entrypoint] WARNING: Tor SOCKS5 not ready after 30s, starting API anyway"\n\
fi\n\
echo "[entrypoint] Starting torDDoS API..."\n\
exec torddos-api' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
