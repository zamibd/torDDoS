#!/usr/bin/env bash
# TorDDoS - Install Script (Updated 2025)
# Supports Ubuntu 22.04 / 24.04 and Termux (Android)

set -e

VENV_DIR="venv"

# ── Detect environment ─────────────────────────────────────────────────────────
if [ -d "/data/data/com.termux" ]; then
    ENV="termux"
else
    ENV="linux"
fi

echo "[*] Detected environment: $ENV"

# ── Install system dependencies ────────────────────────────────────────────────
if [ "$ENV" = "termux" ]; then
    echo "[*] Updating Termux packages..."
    pkg update -y && pkg upgrade -y
    echo "[*] Installing tor and python..."
    pkg install tor python -y
else
    echo "[*] Updating apt packages..."
    sudo apt-get update -y
    echo "[*] Installing tor, python3, pip and venv..."
    sudo apt-get install -y tor python3 python3-pip python3-venv
    echo "[*] Enabling Tor service..."
    sudo systemctl enable tor
    sudo systemctl start tor
fi

# ── Create Python virtual environment ──────────────────────────────────────────
echo "[*] Creating Python virtual environment in ./$VENV_DIR ..."
python3 -m venv "$VENV_DIR"

# ── Install Python requirements ────────────────────────────────────────────────
echo "[*] Installing Python requirements..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r requirements.txt

echo ""
echo "[+] Installation complete!"
echo ""
echo "    To run TorDDoS:"
echo "      source $VENV_DIR/bin/activate"
echo "      python3 torddos.py -t http://example.com -n 10 --threads 3"
echo ""
