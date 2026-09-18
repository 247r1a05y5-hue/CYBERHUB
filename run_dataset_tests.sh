#!/bin/bash
set -e
BACKEND="/mnt/c/Users/vaish/Music/cyber security/backend"
VENV="$BACKEND/.venv"
PYTHON="$VENV/bin/python3"
PYTEST="$VENV/bin/pytest"

cd "$BACKEND"
echo "Running pytest on test_participant_dataset.py..."
"$PYTEST" tests/test_participant_dataset.py -v --tb=short
