#!/bin/bash
# Generate argon2 hash and update users via psql
cd '/mnt/c/Users/vaish/Music/cyber security/backend'

echo "=== Generating password hashes ==="

ADMIN_HASH=$(.venv/bin/python3 -c "from argon2 import PasswordHasher; ph=PasswordHasher(); print(ph.hash('Admin1234!'))")
ANALYST_HASH=$(.venv/bin/python3 -c "from argon2 import PasswordHasher; ph=PasswordHasher(); print(ph.hash('Analyst1234!'))")
VIEWER_HASH=$(.venv/bin/python3 -c "from argon2 import PasswordHasher; ph=PasswordHasher(); print(ph.hash('Viewer1234!'))")

echo "Admin hash: ${ADMIN_HASH:0:30}..."
echo "Analyst hash: ${ANALYST_HASH:0:30}..."

echo "=== Updating DB users ==="
sudo -u postgres psql -d cyberplatform << SQLEOF
-- Show current state
SELECT email, role FROM users;

-- Update emails: .local/.security -> .dev
UPDATE users SET email='admin@cyberhub.dev', hashed_password='$ADMIN_HASH' WHERE email IN ('admin@cyber.local', 'admin@cyberhub.dev');
UPDATE users SET email='analyst@cyberhub.dev', hashed_password='$ANALYST_HASH' WHERE email IN ('analyst@cyber.local', 'analyst@cyberhub.security', 'analyst@cyberhub.dev');
UPDATE users SET email='viewer@cyberhub.dev', hashed_password='$VIEWER_HASH' WHERE email IN ('viewer@cyber.local', 'viewer@cyberhub.dev');

-- Confirm
SELECT email, role, is_active FROM users;
SQLEOF

echo "=== Done — testing login ==="
curl -s -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@cyberhub.dev","password":"Admin1234!"}'
echo ""
