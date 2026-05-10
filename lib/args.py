#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# TorDDos - Updated 2025

import argparse

parser = argparse.ArgumentParser(
    description='TorDDoS - Route stress-test traffic through the Tor network.',
    formatter_class=argparse.RawTextHelpFormatter
)

parser.add_argument(
    '-t', '--target',
    action='store',
    metavar='URL',
    type=str,
    dest='target',
    help='Target URL to attack (e.g. http://example.com)',
    default=None
)

parser.add_argument(
    '-n', '--attempts',
    action='store',
    metavar='N',
    type=int,
    dest='max_attempts',
    default=10,
    help='Number of requests to send (default: 10)'
)

parser.add_argument(
    '--threads',
    action='store',
    metavar='N',
    type=int,
    dest='threads',
    default=3,
    help='Number of concurrent threads (default: 3)'
)