#!/bin/sh
# TorDDoS container entrypoint
# Starts Tor, waits for SOCKS5 port to be ready, then starts the API.

echo "[entrypoint] Starting Tor daemon..."
/etc/init.d/tor start

echo "[entrypoint] Waiting for Tor SOCKS5 port 9050..."
i=0
while [ $i -lt 40 ]; do
    # Use python3 for the port check — avoids nc quoting issues and is always available
    if python3 -c "import socket; s=socket.create_connection(('127.0.0.1',9050),1); s.close()" 2>/dev/null; then
        echo "[entrypoint] Tor SOCKS5 ready."
        break
    fi
    i=$((i+1))
    echo "[entrypoint] Waiting... ($i/40)"
    sleep 1
done

if ! python3 -c "import socket; s=socket.create_connection(('127.0.0.1',9050),1); s.close()" 2>/dev/null; then
    echo "[entrypoint] WARNING: Tor not ready after 40s — starting API anyway (attacks may fail)"
fi

echo "[entrypoint] Starting torDDoS API on port ${PORT:-8080}..."
exec torddos-api
