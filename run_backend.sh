#!/bin/bash
# CyberHub persistent backend runner (nohup, survives session exit)
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

# Ensure Redis is running (no password — simpler for local)
redis-cli ping >/dev/null 2>&1 || redis-server --daemonize yes \
    --logfile /tmp/cyberhub_logs/redis.log \
    --port 6379

# Ensure PostgreSQL is running
sudo service postgresql start 2>/dev/null || true
sleep 1

echo "[backend] Starting uvicorn..."
nohup .venv/bin/uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    > /tmp/cyberhub_logs/api.log 2>&1 &

API_PID=$!
echo "[backend] PID=$API_PID"
echo $API_PID > /tmp/cyberhub_logs/api.pid

echo "[worker] Starting RQ worker..."
nohup .venv/bin/rqworker \
    --url "redis://localhost:6379/0" \
    analyses reports default \
    > /tmp/cyberhub_logs/worker.log 2>&1 &

WORKER_PID=$!
echo "[worker] PID=$WORKER_PID"
echo $WORKER_PID > /tmp/cyberhub_logs/worker.pid

# Wait up to 20s for backend to be ready
echo "Waiting for backend..."
for i in $(seq 1 20); do
    sleep 2
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        echo ""
        echo "========================================="
        echo " CYBERHUB BACKEND IS READY"
        echo "========================================="
        curl -s http://localhost:8000/health
        echo ""
        echo "  Backend  : http://localhost:8000"
        echo "  API docs : http://localhost:8000/api/docs"
        echo "  Logs     : /tmp/cyberhub_logs/api.log"
        exit 0
    fi
    printf "  (%ds)...\r" $((i*2))
done

echo "Backend not ready after 40s — check logs:"
tail -30 /tmp/cyberhub_logs/api.log
exit 1
