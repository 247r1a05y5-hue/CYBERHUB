#!/bin/bash
echo "=== CYBERHUB STATUS CHECK ==="
echo ""

# Health
echo "--- Health ---"
curl -s http://localhost:8000/health

echo ""
echo "--- Login Test ---"
curl -s -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@cyberhub.dev","password":"Admin1234!"}' \
    | python3 -m json.tool 2>/dev/null | head -15

echo ""
echo "--- Running Processes ---"
ps aux | grep -E 'uvicorn|rqworker' | grep -v grep

echo ""
echo "--- Ports ---"
ss -tlnp 2>/dev/null | grep -E '8000|6379|5432' || netstat -tlnp 2>/dev/null | grep -E '8000|6379|5432'
