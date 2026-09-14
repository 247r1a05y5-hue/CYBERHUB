#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
.venv/bin/python3 -u test_phase1.py
