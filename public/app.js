document.addEventListener('DOMContentLoaded', () => {
    const btnStart = document.getElementById('btnStart');
    const btnStop = document.getElementById('btnStop');
    const inputTarget = document.getElementById('targetUrl');
    const inputAttempts = document.getElementById('attempts');
    const inputThreads = document.getElementById('threads');
    const inputApiKey = document.getElementById('apiKey');
    
    const statusText = document.getElementById('statusText');
    const torStatus = document.getElementById('torStatus');
    const statusTarget = document.getElementById('statusTarget');
    const statusStarted = document.getElementById('statusStarted');
    const consoleOutput = document.getElementById('consoleOutput');

    let eventSource = null;

    // Helper for API headers
    const getHeaders = () => {
        const headers = { 'Content-Type': 'application/json' };
        const key = inputApiKey.value.trim();
        if (key) {
            headers['X-API-Key'] = key;
        }
        return headers;
    };

    // Append log to console
    const appendLog = (msg, type = '') => {
        const div = document.createElement('div');
        div.className = `log-line ${type}`;
        div.textContent = msg;
        consoleOutput.appendChild(div);
        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    };

    // Update UI based on running state
    const setRunningState = (isRunning, data = null) => {
        btnStart.disabled = isRunning;
        btnStop.disabled = !isRunning;
        inputTarget.disabled = isRunning;
        inputAttempts.disabled = isRunning;
        inputThreads.disabled = isRunning;

        if (isRunning && data) {
            statusText.textContent = 'Running';
            statusText.className = 'status-running';
            statusTarget.textContent = data.target || '-';
            const started = new Date(data.started_at);
            statusStarted.textContent = started.toLocaleTimeString();
        } else {
            statusText.textContent = 'Idle';
            statusText.className = 'status-idle';
            statusTarget.textContent = '-';
            statusStarted.textContent = '-';
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
        }
    };

    // Check Tor Status
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
            }
        } catch (err) {
            torStatus.textContent = 'Offline';
            torStatus.style.color = 'var(--danger)';
        }
    };

    // Sync Attack Status
    const syncStatus = async () => {
        try {
            const res = await fetch('/api/attack/status', { headers: getHeaders() });
            if (res.ok) {
                const data = await res.json();
                setRunningState(data.running, data);
                if (data.running && !eventSource) {
                    startLogStream();
                }
            }
        } catch (err) {
            console.error('Failed to sync status:', err);
        }
    };

    // Start Server-Sent Events for logs
    const startLogStream = () => {
        if (eventSource) eventSource.close();

        // EventSource cannot send custom headers — pass API key as ?token= query param
        const key = inputApiKey.value.trim();
        const sseUrl = key ? `/api/attack/logs?token=${encodeURIComponent(key)}` : '/api/attack/logs';
        eventSource = new EventSource(sseUrl);
        
        eventSource.onmessage = (e) => {
            let type = '';
            if (e.data.includes('[!]')) type = 'log-error';
            if (e.data.includes('[*]')) type = 'log-info';
            appendLog(e.data, type);
        };

        // Named 'done' event sent by server when attack finishes
        eventSource.addEventListener('done', (e) => {
            setRunningState(false);
            appendLog('Attack completed.', 'log-info');
            checkTorStatus();
            eventSource.close();
            eventSource = null;
        });

        eventSource.onerror = () => {
            // If attack is no longer running, clean up; otherwise keep retrying
            if (!btnStop.disabled) {
                eventSource.close();
                eventSource = null;
            }
        };
    };

    // Start Attack
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
                    target: inputTarget.value,
                    attempts: parseInt(inputAttempts.value),
                    threads: parseInt(inputThreads.value)
                })
            });

            const data = await res.json();
            if (res.ok) {
                // Open log stream immediately — don't wait for status poll
                startLogStream();
                // Poll status to update UI (running state, timestamps)
                let polls = 0;
                const pollUntilRunning = setInterval(async () => {
                    await syncStatus();
                    polls++;
                    if (polls > 10) clearInterval(pollUntilRunning);
                }, 1000);
                checkTorStatus();
            } else {
                appendLog(`Error: ${data.error}`, 'log-error');
                btnStart.disabled = false;
            }
        } catch (err) {
            appendLog(`Request failed: ${err.message}`, 'log-error');
            btnStart.disabled = false;
        }
    });

    // Stop Attack
    btnStop.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/attack/stop', {
                method: 'POST',
                headers: getHeaders()
            });
            const data = await res.json();
            if (res.ok) {
                const msg = data.already_stopped
                    ? 'Attack had already stopped.'
                    : 'Stop signal sent.';
                appendLog(msg, 'log-info');
                // Always reset UI — attack may have finished before stop was clicked
                setRunningState(false);
                if (eventSource) {
                    eventSource.close();
                    eventSource = null;
                }
            } else {
                appendLog(`Stop failed: ${data.error || res.status}`, 'log-error');
            }
        } catch (err) {
            appendLog(`Stop request failed: ${err.message}`, 'log-error');
        }
    });

    // Initial sync
    checkTorStatus();
    syncStatus();

    // Auto-refresh Tor status periodically
    setInterval(checkTorStatus, 5000);
});
