# TorDDoS API Documentation

The TorDDoS project provides a RESTful API to manage, monitor, and stream logs of the attack process. By default, the API is accessible on `http://localhost:8080`.

## Authentication (Optional but Recommended)

If the `API_KEY` environment variable is set on the server, all endpoints (except `/api/health`) will require authentication.

Pass the key using the `X-API-Key` HTTP header:
```bash
curl -H "X-API-Key: your_super_secret_api_key_here" http://localhost:8080/api/tor/status
```

---

## 1. Health Check

Checks if the API service is up and running.

**Endpoint:** `GET /api/health`

**Example Request:**
```bash
curl -s http://localhost:8080/api/health
```

**Example Response:**
```json
{
  "service": "torDDoS API",
  "status": "ok",
  "version": "2.0.0"
}
```

---

## 2. Tor Status

Checks the status of the local Tor installation and background service.

**Endpoint:** `GET /api/tor/status`

**Example Request:**
```bash
curl -s http://localhost:8080/api/tor/status
```

**Example Response:**
```json
{
  "installed": true,
  "path": "/usr/sbin/tor",
  "running": false
}
```

---

## 3. Start Attack

Starts the TorDDoS worker in the background.

**Endpoint:** `POST /api/attack/start`

**Headers:**
- `Content-Type: application/json`

**Body Parameters:**
- `target` (string, required): The target URL to test.
- `attempts` (integer, optional): Total number of requests to send. Default is `10`.
- `threads` (integer, optional): Number of concurrent threads. Default is `3`.

**Example Request:**
```bash
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "target": "http://example.com",
    "attempts": 50,
    "threads": 5
  }'
```

**Example Response (Success):**
```json
{
  "message": "attack started",
  "target": "http://example.com",
  "attempts": 50,
  "threads": 5
}
```

**Example Response (Conflict - Already Running):**
```json
{
  "error": "an attack is already running"
}
```

---

## 4. Get Attack Status

Gets the current status of the attack worker and retrieves the most recent console logs.

**Endpoint:** `GET /api/attack/status`

**Example Request:**
```bash
curl -s http://localhost:8080/api/attack/status
```

**Example Response (Idle):**
```json
{
  "running": false,
  "target": "",
  "attempts": 0,
  "threads": 0,
  "started_at": "0001-01-01T00:00:00Z",
  "recent_logs": []
}
```

**Example Response (Running):**
```json
{
  "running": true,
  "target": "http://example.com",
  "attempts": 50,
  "threads": 5,
  "started_at": "2026-05-10T00:36:58.777Z",
  "recent_logs": [
    "[!] Starting attack on http://example.com",
    "[!] Max attempts: 50 | Threads: 5"
  ]
}
```

---

## 5. Stop Attack

Forcefully stops the currently running attack.

**Endpoint:** `POST /api/attack/stop`

**Example Request:**
```bash
curl -X POST http://localhost:8080/api/attack/stop
```

**Example Response:**
```json
{
  "message": "attack stopped"
}
```

**Example Response (If Not Running):**
```json
{
  "error": "no attack is currently running"
}
```

---

## 6. Stream Attack Logs (SSE)

Connects to a Server-Sent Events (SSE) stream for real-time console output of the TorDDoS attack. Perfect for building live UIs.

**Endpoint:** `GET /api/attack/logs`

**Example Request (Browser or Curl):**
```bash
curl -N http://localhost:8080/api/attack/logs
```

**Example Output:**
```text
data: [!] Starting attack on http://example.com

data: [!] Max attempts: 50 | Threads: 5

data: [!] Tor service is not running. Attempting to start it...

data: [+] [1/50] Target: http://example.com

data: [*] Getting data from http://example.com...

event: done
data: attack finished
```
