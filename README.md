# TorDDoS

![Version](https://img.shields.io/badge/version-v2.0-orange.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/license-GPL%203.0-brightgreen.svg)
![Updated](https://img.shields.io/badge/updated-2025-yellow.svg)

> A Python 3 tool to send stress-test traffic through the Tor network, rotating exit nodes between requests for anonymity.  
> Originally created by [R3nt0n](https://github.com/R3nt0n) in 2019 — updated to Python 3 with multi-threading, modern user-agents, and improved reliability.

---

## Features

- ✅ **Python 3.8+** — fully rewritten from Python 2
- ✅ **Multi-threaded** — concurrent requests via `--threads`
- ✅ **Automatic Tor identity rotation** — new exit node per request
- ✅ **Modern User-Agent pool** — Chrome 120, Firefox 120, Safari 17, Edge 120, mobile agents
- ✅ **DNS-over-Tor** (`socks5h://`) — no DNS leaks
- ✅ **Multiple IP-check fallbacks** — reliable exit node verification
- ✅ **Auto-installer** — detects Ubuntu/Debian or Termux automatically

---

## How It Works

1. Starts (or restarts) the Tor service to obtain a fresh exit node.
2. Verifies the new exit IP is unique (not used before in this session).
3. Creates a `requests` session routed through `socks5h://127.0.0.1:9050`.
4. Sends a GET request to the target with a randomized modern browser User-Agent.
5. Repeats until the configured number of attempts is reached, using concurrent threads.

---

## Requirements

| Requirement | Version |
|---|---|
| Python | 3.8+ |
| Tor | Any recent version |
| OS | Ubuntu 22.04 / 24.04, Debian, or Termux (Android) |

**Python packages** (installed automatically):
```
requests>=2.31.0
beautifulsoup4>=4.12.0
PySocks>=1.7.1
urllib3>=2.0.0
```

---

## Installation

### Docker (Recommended)

The easiest way to run the full project (including the Go RESTful API and the Python worker) is using Docker Compose.

```bash
git clone https://github.com/zamibd/torDDoS.git
cd torDDoS
docker compose up -d
```
The API will be available at `http://localhost:8080`.

> **Note on Security**: For production, edit `docker-compose.yml` to uncomment and set the `API_KEY` and `ALLOWED_ORIGINS` environment variables to protect your API endpoints.

### Ubuntu / Debian (22.04 / 24.04)

```bash
git clone https://github.com/zamibd/torDDoS.git
cd torDDoS
bash install.sh
```

The installer will:
- Install `tor`, `python3`, `python3-venv` via `apt`
- Enable and start the Tor systemd service
- Create a Python virtual environment (`./venv`)
- Install all Python requirements inside it

### Termux (Android)

```bash
git clone https://github.com/zamibd/torDDoS.git
cd torDDoS
bash install.sh
```

The installer auto-detects Termux and uses `pkg` instead of `apt`.

### Manual Setup

```bash
# 1. Install system dependencies
sudo apt install tor python3 python3-venv -y   # Ubuntu/Debian
# pkg install tor python -y                    # Termux

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install Python requirements
pip install -r requirements.txt
```

---

## Usage

```
python3 torddos.py -t <TARGET_URL> [-n <ATTEMPTS>] [--threads <N>]
```

### Arguments

| Flag | Description | Default |
|---|---|---|
| `-t`, `--target` | Target URL (required) | — |
| `-n`, `--attempts` | Total number of requests to send | `10` |
| `--threads` | Number of concurrent threads | `3` |
| `-h`, `--help` | Show help message | — |

### Examples

```bash
# Activate virtual environment first
source venv/bin/activate

# Basic usage — 10 requests, 3 threads
python3 torddos.py -t http://example.com

# 50 requests with 5 concurrent threads
python3 torddos.py -t http://example.com -n 50 --threads 5

# Show help
python3 torddos.py --help
```

### API Documentation

The project includes a Go-based RESTful API running on port `8080` (or the port defined in `PORT`).
For a complete list of all endpoints, parameters, and examples, please see the **[API Documentation](API.md)**.

---

## Project Structure

```
torDDoS/
├── torddos.py          # Main entry point
├── install.sh          # Auto-installer (Ubuntu + Termux)
├── requirements.txt    # Python dependencies
├── README.md
└── lib/
    ├── __init__.py
    ├── args.py         # CLI argument parser
    ├── color.py        # Terminal color codes
    └── tor.py          # Tor session management class
```

---

## Legal Disclaimer

This tool is created **for educational and security research purposes only**.  
Do **NOT** use it against any system you do not own or have explicit written permission to test.  
The author is not responsible for any misuse or damage caused by this software.  
**You use this software entirely at your own risk.**
