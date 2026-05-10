#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# TorDDos - Updated 2025

import time
import shutil
import subprocess
import requests
import socket
from random import choice
from lib.color import color


class Tor:
    def __init__(self, addr: str = '127.0.0.1', port: str = '9050'):
        self.used_proxies: list = []
        self.addr = addr
        self.port = port

    def _run(self, cmd: str) -> int:
        """Run a shell command and return its exit code."""
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode

    def tor_installed(self) -> bool:
        """Check if Tor binary is available on PATH."""
        return shutil.which('tor') is not None

    def tor_started(self) -> bool:
        """Check if the Tor systemd service is active."""
        return self._run('systemctl is-active --quiet tor') == 0

    def start_tor(self) -> None:
        """Start the Tor service."""
        self._run('sudo systemctl start tor')

    def restart_tor(self) -> None:
        """Send a NEWNYM signal to the Tor Control Port to get a new identity/exit node."""
        try:
            s = socket.socket()
            s.connect(('127.0.0.1', 9051))
            s.send(b'AUTHENTICATE\r\n')
            s.send(b'SIGNAL NEWNYM\r\n')
            s.close()
        except Exception as e:
            print(f"{color.RED}[!]{color.END} Failed to send NEWNYM signal: {e}")

    def stop_tor(self) -> None:
        """Stop the Tor service."""
        self._run('sudo systemctl stop tor')

    def get_tor_session(self) -> requests.Session:
        """Create a requests session routed through Tor SOCKS5 proxy."""
        s = requests.Session()
        proxy_url = f'socks5h://{self.addr}:{self.port}'
        s.proxies = {'http': proxy_url, 'https': proxy_url}
        s.headers.update({'User-Agent': self.pick_user_agent()})
        s.verify = True
        return s

    def pick_user_agent(self) -> str:
        """Return a random modern browser User-Agent string."""
        USER_AGENTS = [
            # Chrome 120+ on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            # Chrome on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            # Chrome on Linux
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            # Firefox 120+ on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0',
            # Firefox on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.1; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 13.5; rv:119.0) Gecko/20100101 Firefox/119.0',
            # Firefox on Linux
            'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
            # Safari on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            # Edge on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
            # Mobile Chrome (Android)
            'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',
            # Mobile Safari (iPhone)
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        ]
        return choice(USER_AGENTS)

    def get_current_ip(self, session: requests.Session) -> str | None:
        """Fetch the current Tor exit node's public IP address."""
        ip_services = [
            'https://api.ipify.org',
            'https://ifconfig.me/ip',
            'https://icanhazip.com',
            'https://ip.42.pl/raw',
        ]
        for service in ip_services:
            try:
                ip = session.get(service, timeout=10).text.strip()
                if ip:
                    return ip
            except Exception:
                continue
        return None

    def _tor_reachable(self) -> bool:
        """Return True if the local Tor SOCKS5 proxy is accepting connections."""
        try:
            s = socket.create_connection((self.addr, int(self.port)), timeout=3)
            s.close()
            return True
        except OSError:
            return False

    def new_session(self) -> requests.Session | None:
        """
        Send NEWNYM to rotate the Tor circuit and return a new session.
        Skips the slow external IP-check; just verifies the SOCKS5 port is up.
        Retries up to 5 times before giving up.
        """
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            self.restart_tor()          # sends NEWNYM via control port
            time.sleep(1)              # brief pause for circuit to stabilise

            if self._tor_reachable():
                print(f'{color.BLUE}[!]{color.END} Tor circuit ready (attempt {attempt})')
                return self.get_tor_session()

            print(f'{color.YELLOW}[!]{color.END} Tor SOCKS5 not reachable yet (attempt {attempt}/{max_retries}). Retrying...')

        print(f'{color.RED}[!]{color.END} Could not reach Tor SOCKS5 proxy after {max_retries} attempts.')
        return None