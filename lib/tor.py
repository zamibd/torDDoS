#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# TorDDos - Updated 2025

import time
import threading
import shutil
import subprocess
import requests
import socket
from random import choice
from lib.color import color


class Tor:
    """
    Manages Tor connectivity for the TorDDoS attack engine.

    Design:
    - A shared requests.Session is pre-built once and reused by all threads.
      This avoids the thundering-herd problem where N threads simultaneously
      send NEWNYM signals and destroy each other's circuits.
    - Circuit rotation (NEWNYM) is serialised via _rotate_lock and respects
      Tor's minimum 10-second inter-NEWNYM interval.
    - Individual thread workers call get_session() which returns the shared
      session instantly (no blocking wait per request).
    """

    # Tor enforces a minimum 10-second gap between NEWNYM signals.
    _NEWNYM_COOLDOWN = 10.0

    def __init__(self, addr: str = '127.0.0.1', port: str = '9050'):
        self.addr = addr
        self.port = port
        self._session: requests.Session | None = None
        self._session_lock = threading.Lock()
        self._rotate_lock  = threading.Lock()
        self._last_newnym  = 0.0          # epoch seconds of last NEWNYM

    # ── Low-level helpers ─────────────────────────────────────────────────────

    def _run(self, cmd: str) -> int:
        """Run a shell command and return its exit code."""
        result = subprocess.run(cmd, shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode

    def _tor_reachable(self, timeout: float = 3.0) -> bool:
        """Return True if the local Tor SOCKS5 proxy is accepting connections."""
        try:
            s = socket.create_connection((self.addr, int(self.port)), timeout=timeout)
            s.close()
            return True
        except OSError:
            return False

    def _send_newnym(self) -> None:
        """Send NEWNYM to the Tor Control Port (unauthenticated, cookie-auth disabled)."""
        try:
            with socket.create_connection(('127.0.0.1', 9051), timeout=5) as s:
                s.sendall(b'AUTHENTICATE\r\n')
                time.sleep(0.1)
                s.sendall(b'SIGNAL NEWNYM\r\n')
                time.sleep(0.1)
        except Exception as e:
            print(f'{color.YELLOW}[!]{color.END} NEWNYM failed (non-fatal): {e}')

    # ── Tor service management ────────────────────────────────────────────────

    def tor_installed(self) -> bool:
        """Check if Tor binary is available on PATH."""
        return shutil.which('tor') is not None

    def tor_started(self) -> bool:
        """Check if the Tor service is running (works with mock systemctl)."""
        return self._run('systemctl is-active --quiet tor') == 0

    def start_tor(self) -> None:
        """Start the Tor service and wait up to 30 s for SOCKS5 to become ready."""
        self._run('sudo systemctl start tor')
        print(f'{color.YELLOW}[!]{color.END} Waiting for Tor SOCKS5 port...')
        for _ in range(30):
            if self._tor_reachable(timeout=1.0):
                print(f'{color.GREEN}[*]{color.END} Tor SOCKS5 ready.')
                return
            time.sleep(1)
        print(f'{color.RED}[!]{color.END} Tor SOCKS5 did not become ready in 30 s.')

    def stop_tor(self) -> None:
        """Stop the Tor service."""
        self._run('sudo systemctl stop tor')

    # ── Session management ────────────────────────────────────────────────────

    def _build_session(self) -> requests.Session:
        """Create a new requests.Session routed through Tor SOCKS5."""
        s = requests.Session()
        proxy_url = f'socks5h://{self.addr}:{self.port}'
        s.proxies = {'http': proxy_url, 'https': proxy_url}
        s.headers.update({'User-Agent': self.pick_user_agent()})
        s.verify = True
        return s

    def get_session(self) -> requests.Session | None:
        """
        Return the shared Tor session, initialising it on first call.
        Returns None if Tor is not reachable.
        """
        with self._session_lock:
            if self._session is None:
                if not self._tor_reachable():
                    return None
                self._session = self._build_session()
                print(f'{color.BLUE}[!]{color.END} Tor session initialised.')
            return self._session

    def rotate_circuit(self) -> None:
        """
        Rotate the Tor exit node (NEWNYM), respecting the 10-second cooldown.
        Thread-safe — concurrent callers will block until rotation is done.
        """
        with self._rotate_lock:
            elapsed = time.time() - self._last_newnym
            if elapsed < self._NEWNYM_COOLDOWN:
                wait = self._NEWNYM_COOLDOWN - elapsed
                print(f'{color.YELLOW}[!]{color.END} Waiting {wait:.1f}s before NEWNYM...')
                time.sleep(wait)

            self._send_newnym()
            self._last_newnym = time.time()
            print(f'{color.BLUE}[!]{color.END} Tor circuit rotated (NEWNYM sent).')

            # Rebuild session with fresh User-Agent for the new circuit
            with self._session_lock:
                self._session = self._build_session()

    # ── Legacy API (kept for compatibility) ───────────────────────────────────

    def restart_tor(self) -> None:
        """Alias for rotate_circuit() — rotates the Tor exit node."""
        self.rotate_circuit()

    def new_session(self) -> requests.Session | None:
        """Legacy: return a session (uses shared session, no per-call NEWNYM)."""
        return self.get_session()

    def get_tor_session(self) -> requests.Session:
        """Build and return a fresh session (does not replace the shared one)."""
        return self._build_session()

    # ── User-Agent pool ───────────────────────────────────────────────────────

    def pick_user_agent(self) -> str:
        """Return a random modern browser User-Agent string."""
        USER_AGENTS = [
            # Chrome on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            # Chrome on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # Chrome on Linux
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # Firefox on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            # Firefox on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.1; rv:120.0) Gecko/20100101 Firefox/120.0',
            # Firefox on Linux
            'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
            # Safari on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            # Edge on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            # Mobile Chrome (Android)
            'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36',
            # Mobile Safari (iPhone)
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
        ]
        return choice(USER_AGENTS)

    def get_current_ip(self, session: requests.Session) -> str | None:
        """Fetch the current Tor exit node's public IP address."""
        for service in ['https://api.ipify.org', 'https://icanhazip.com']:
            try:
                ip = session.get(service, timeout=10).text.strip()
                if ip:
                    return ip
            except Exception:
                continue
        return None