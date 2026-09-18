#!/bin/bash
sleep 15
echo "=== Health ==="
curl -s http://localhost:8000/health

echo ""
echo "=== Login admin@cyberhub.dev ==="
curl -s -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@cyberhub.dev","password":"Admin1234!"}' \
    | python3 -m json.tool 2>/dev/null
