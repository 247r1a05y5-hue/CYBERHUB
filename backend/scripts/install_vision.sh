#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
echo "Locating uv and python..."
which uv || find / -name uv 2>/dev/null
uv pip install --python "/mnt/c/Users/vaish/Music/cyber security/backend/.venv" google-cloud-vision google-auth
