document.addEventListener('DOMContentLoaded', () => {
    const btnStart     = document.getElementById('btnStart');
    const btnStop      = document.getElementById('btnStop');
    const inputTarget  = document.getElementById('targetUrl');
    const inputAttempts = document.getElementById('attempts');
    const inputThreads = document.getElementById('threads');
    const inputApiKey  = document.getElementById('apiKey');

    const statusText   = document.getElementById('statusText');
    const torStatus    = document.getElementById('torStatus');
    const statusTarget = document.getElementById('statusTarget');
    const statusStarted = document.getElementById('statusStarted');
    const consoleOutput = document.getElementById('consoleOutput');

    let eventSource = null;

    // ── Persist API key in localStorage ──────────────────────────────────────
    const STORAGE_KEY = 'torddos_api_key';
    const savedKey = localStorage.getItem(STORAGE_KEY);
    if (savedKey) inputApiKey.value = savedKey;

    inputApiKey.addEventListener('change', () => {
        const k = inputApiKey.value.trim();
        if (k) localStorage.setItem(STORAGE_KEY, k);
        else   localStorage.removeItem(STORAGE_KEY);
    });

    // ── Helper for API headers ────────────────────────────────────────────────
    const getHeaders = () => {
        const headers = { 'Content-Type': 'application/json' };
        const key = inputApiKey.value.trim();
        if (key) headers['X-API-Key'] = key;
        return headers;
    };

    // ── 401 banner ────────────────────────────────────────────────────────────
    let authBannerShown = false;
    const showAuthBanner = () => {
        if (authBannerShown) return;
        authBannerShown = true;
        appendLog('⚠ API key required — enter your key in the API Key field and retry.', 'log-error');
        inputApiKey.style.outline = '2px solid var(--danger)';
        inputApiKey.focus();
    };
    inputApiKey.addEventListener('input', () => {
        authBannerShown = false;
        inputApiKey.style.outline = '';
    });

    // ── Append log to console ─────────────────────────────────────────────────
    const appendLog = (msg, type = '') => {
        const div = document.createElement('div');
        div.className = `log-line ${type}`;
        div.textContent = msg;
        consoleOutput.appendChild(div);
        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    };

    // ── Safe EventSource cleanup (prevents null-ref errors) ───────────────────
    const closeEventSource = () => {
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
    };

    // ── Update UI based on running state ──────────────────────────────────────
    const setRunningState = (isRunning, data = null) => {
        btnStart.disabled  = isRunning;
        btnStop.disabled   = !isRunning;
        inputTarget.disabled  = isRunning;
        inputAttempts.disabled = isRunning;
        inputThreads.disabled  = isRunning;

        if (isRunning && data) {
            statusText.textContent = 'Running';
            statusText.className   = 'status-running';
            statusTarget.textContent = data.target || '-';
            statusStarted.textContent = new Date(data.started_at).toLocaleTimeString();
        } else {
            statusText.textContent = 'Idle';
            statusText.className   = 'status-idle';
            statusTarget.textContent  = '-';
            statusStarted.textContent = '-';
            closeEventSource();
        }
    };

    // ── Check Tor Status ──────────────────────────────────────────────────────
    const checkTorStatus = async () => {
        try {
            const res = await fetch('/api/tor/status', { headers: getHeaders() });
            if (res.ok) {
                const data = await res.json();
                torStatus.textContent = data.running ? 'Running' : 'Installed, Stopped';
                torStatus.style.color = data.running ? 'var(--success)' : 'var(--text-main)';
            } else if (res.status === 401) {
                torStatus.textContent = 'Auth Required';
                torStatus.style.color = 'var(--danger)';
                showAuthBanner();
            }
        } catch {
            torStatus.textContent = 'Offline';
            torStatus.style.color = 'var(--danger)';
        }
    };

    // ── Sync Attack Status ────────────────────────────────────────────────────
    const syncStatus = async () => {
        try {
            const res = await fetch('/api/attack/status', { headers: getHeaders() });
            if (res.ok) {
                const data = await res.json();
                setRunningState(data.running, data);
                if (data.running && !eventSource) startLogStream();
            } else if (res.status === 401) {
                showAuthBanner();
            }
        } catch (err) {
            console.error('Failed to sync status:', err);
        }
    };

    // ── SSE log stream ────────────────────────────────────────────────────────
    const startLogStream = () => {
        closeEventSource(); // clean up any prior connection

        const key = inputApiKey.value.trim();
        const sseUrl = key
            ? `/api/attack/logs?token=${encodeURIComponent(key)}`
            : '/api/attack/logs';

        eventSource = new EventSource(sseUrl);

        eventSource.onmessage = (e) => {
            let type = '';
            if (e.data.includes('[!]')) type = 'log-error';
            else if (e.data.includes('[*]')) type = 'log-info';
            appendLog(e.data, type);
        };

        // Server sends `event: done` when the attack finishes
        eventSource.addEventListener('done', () => {
            closeEventSource();        // null eventSource FIRST
            setRunningState(false);    // this also calls closeEventSource (safe no-op)
            appendLog('Attack completed.', 'log-info');
            checkTorStatus();
        });

        eventSource.onerror = () => {
            // Guard: already cleaned up by done handler or stop button
            if (!eventSource) return;

            // btnStop.disabled === true means attack is NOT running → clean up
            if (btnStop.disabled) {
                closeEventSource();
            }
            // If attack IS still running, let EventSource auto-retry
        };
    };

    // ── Start Attack ──────────────────────────────────────────────────────────
    btnStart.addEventListener('click', async () => {
        if (!inputTarget.value) {
            alert('Please enter a target URL');
            return;
        }

        consoleOutput.innerHTML = '';
        appendLog('Initializing attack...', 'log-info');
        btnStart.disabled = true;

        try {
            const res = await fetch('/api/attack/start', {
                method: 'POST',
                headers: getHeaders(),
                body: JSON.stringify({
                    target:   inputTarget.value,
                    attempts: parseInt(inputAttempts.value),
                    threads:  parseInt(inputThreads.value),
                }),
            });

            const data = await res.json();
            if (res.ok) {
                startLogStream();
                let polls = 0;
                const poll = setInterval(async () => {
                    await syncStatus();
                    if (++polls > 10) clearInterval(poll);
                }, 1000);
                checkTorStatus();
            } else if (res.status === 401) {
                showAuthBanner();
                appendLog('Error: API key required.', 'log-error');
                btnStart.disabled = false;
            } else {
                appendLog(`Error: ${data.error}`, 'log-error');
                btnStart.disabled = false;
            }
        } catch (err) {
            appendLog(`Request failed: ${err.message}`, 'log-error');
            btnStart.disabled = false;
        }
    });

    // ── Stop Attack ───────────────────────────────────────────────────────────
    btnStop.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/attack/stop', {
                method: 'POST',
                headers: getHeaders(),
            });
            const data = await res.json();
            if (res.ok) {
                appendLog(
                    data.already_stopped ? 'Attack had already stopped.' : 'Stop signal sent.',
                    'log-info'
                );
                setRunningState(false);
                closeEventSource();
            } else if (res.status === 401) {
                showAuthBanner();
            } else {
                appendLog(`Stop failed: ${data.error || res.status}`, 'log-error');
            }
        } catch (err) {
            appendLog(`Stop request failed: ${err.message}`, 'log-error');
        }
    });

    // ── Initial sync ──────────────────────────────────────────────────────────
    checkTorStatus();
    syncStatus();
    setInterval(checkTorStatus, 5000);
});
