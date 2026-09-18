#!/bin/bash
set -e

BACKEND_DIR="/mnt/c/Users/vaish/Music/cyber security/backend"
VENV="$BACKEND_DIR/.venv/bin"
LOG_DIR="/tmp/cyberhub_logs"
mkdir -p "$LOG_DIR"

echo "=== CyberHub Startup Script ==="

# ── 1. Install Redis and PostgreSQL if missing ───────────────────────────────
echo "[1/6] Checking/installing Redis and PostgreSQL..."
if ! command -v redis-server &>/dev/null; then
    echo "Installing Redis..."
    sudo apt-get update -qq && sudo apt-get install -y -qq redis-server
fi
if ! command -v psql &>/dev/null; then
    echo "Installing PostgreSQL..."
    sudo apt-get update -qq && sudo apt-get install -y -qq postgresql postgresql-contrib
fi
echo "  Redis: $(redis-server --version)"
echo "  PostgreSQL: $(psql --version)"

# ── 2. Start Redis ───────────────────────────────────────────────────────────
echo "[2/6] Starting Redis..."
if ! redis-cli ping &>/dev/null 2>&1; then
    redis-server --daemonize yes --logfile "$LOG_DIR/redis.log" --port 6379 \
        --requirepass "redis_changeme" --maxmemory 256mb --maxmemory-policy allkeys-lru
    sleep 2
fi
redis-cli -a redis_changeme ping && echo "  Redis: PONG ✓" || echo "  Redis: failed"

# ── 3. Start PostgreSQL ──────────────────────────────────────────────────────
echo "[3/6] Starting PostgreSQL..."
sudo service postgresql start || true
sleep 3

# Create user and database if not exist
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='cyberuser'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER cyberuser WITH PASSWORD 'cyberpass_changeme';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='cyberplatform'" | grep -q 1 || \
    sudo -u postgres createdb -O cyberuser cyberplatform
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE cyberplatform TO cyberuser;" 2>/dev/null || true
echo "  PostgreSQL: ready ✓"

# ── 4. Run Alembic / DB Init ─────────────────────────────────────────────────
echo "[4/6] Initialising database schema..."
cd "$BACKEND_DIR"
DATABASE_URL="postgresql+asyncpg://cyberuser:cyberpass_changeme@localhost:5432/cyberplatform" \
REDIS_URL="redis://:redis_changeme@localhost:6379/0" \
    "$VENV/python" -c "from app.main import app; print('  Import OK ✓')"

# ── 5. Start Backend API ─────────────────────────────────────────────────────
echo "[5/6] Starting FastAPI backend on port 8000..."
cd "$BACKEND_DIR"
APP_ENV=development \
APP_DEBUG=true \
APP_SECRET_KEY=dev_secret_key_cyber_platform_98472948729384 \
JWT_SECRET_KEY=dev_jwt_secret_cyber_platform_98472948729384 \
DATABASE_URL="postgresql+asyncpg://cyberuser:cyberpass_changeme@localhost:5432/cyberplatform" \
REDIS_URL="redis://:redis_changeme@localhost:6379/0" \
CORS_ORIGINS="http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173" \
STORAGE_ROOT="/tmp/cyberhub_storage" \
QUARANTINE_ROOT="/tmp/cyberhub_quarantine" \
ALLOW_DEMO_SEEDING=true \
PUBLIC_BASE_URL="http://localhost:8000" \
ALLOW_TEST_MOCK_PROVIDER=true \
PORT=8000 \
    "$VENV/uvicorn" app.main:app --host 0.0.0.0 --port 8000 --log-level info > "$LOG_DIR/api.log" 2>&1 &
API_PID=$!
echo "  Backend PID: $API_PID (logs: $LOG_DIR/api.log)"

# ── 6. Start RQ Worker ───────────────────────────────────────────────────────
echo "[6/6] Starting RQ Worker..."
cd "$BACKEND_DIR"
APP_ENV=development \
APP_SECRET_KEY=dev_secret_key_cyber_platform_98472948729384 \
JWT_SECRET_KEY=dev_jwt_secret_cyber_platform_98472948729384 \
DATABASE_URL="postgresql+asyncpg://cyberuser:cyberpass_changeme@localhost:5432/cyberplatform" \
REDIS_URL="redis://:redis_changeme@localhost:6379/0" \
STORAGE_ROOT="/tmp/cyberhub_storage" \
PUBLIC_BASE_URL="http://localhost:8000" \
    "$VENV/rqworker" --url "redis://:redis_changeme@localhost:6379/0" analyses reports default > "$LOG_DIR/worker.log" 2>&1 &
WORKER_PID=$!
echo "  Worker PID: $WORKER_PID (logs: $LOG_DIR/worker.log)"

# ── Wait and check health ────────────────────────────────────────────────────
echo ""
echo "Waiting for backend to be ready..."
for i in $(seq 1 30); do
    sleep 2
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        echo "✓ Backend is READY at http://localhost:8000"
        curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null | head -5
        break
    fi
    printf "  waiting... ${i}/30\r"
done

echo ""
echo "=== CyberHub is running ==="
echo "  Frontend : http://localhost:5173"
echo "  Backend  : http://localhost:8000"
echo "  API docs : http://localhost:8000/api/docs (dev only)"
echo "  API logs : $LOG_DIR/api.log"
echo "  Worker   : $LOG_DIR/worker.log"
echo ""
echo "Default login: admin@cyber.local / Admin1234!"
