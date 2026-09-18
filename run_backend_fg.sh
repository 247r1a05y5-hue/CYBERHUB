#!/bin/bash
# Foreground runner — keeps uvicorn alive as long as this script runs
# Called with IsDaemon=true from Windows so it stays alive

cd '/mnt/c/Users/vaish/Music/cyber security/backend'
mkdir -p /tmp/cyberhub_storage /tmp/cyberhub_quarantine /tmp/cyberhub_logs

export APP_ENV=development
export APP_DEBUG=true
export APP_SECRET_KEY=dev_secret_key_cyber_platform_98472948729384
export JWT_SECRET_KEY=dev_jwt_secret_cyber_platform_98472948729384
export DATABASE_URL='postgresql+asyncpg://cyberuser:cyberpass_changeme@localhost:5432/cyberplatform'
export REDIS_URL='redis://localhost:6379/0'
export CORS_ORIGINS='http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://192.168.1.5:5173'
export STORAGE_ROOT='/tmp/cyberhub_storage'
export QUARANTINE_ROOT='/tmp/cyberhub_quarantine'
export ALLOW_DEMO_SEEDING=true
export PUBLIC_BASE_URL='http://localhost:8000'
export ALLOW_TEST_MOCK_PROVIDER=true
export PORT=8000

# Start Redis if not running
redis-cli ping >/dev/null 2>&1 || redis-server --daemonize yes \
    --logfile /tmp/cyberhub_logs/redis.log --port 6379

# Start PostgreSQL if not running
sudo service postgresql start 2>/dev/null || true
sleep 1

# Start RQ worker in background
nohup .venv/bin/rqworker \
    --url "redis://localhost:6379/0" \
    analyses reports default \
    > /tmp/cyberhub_logs/worker.log 2>&1 &
echo "[worker] PID=$!"

# Run uvicorn in FOREGROUND so process stays alive
echo "[backend] Starting uvicorn (foreground)..."
exec .venv/bin/uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info
