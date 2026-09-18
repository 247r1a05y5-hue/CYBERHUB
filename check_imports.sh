#!/bin/bash
set -e
BACKEND="/mnt/c/Users/vaish/Music/cyber security/backend"
VENV="$BACKEND/.venv"
PYTHON="$VENV/bin/python3"
PIP="$VENV/bin/pip3"

echo "Installing boto3 and imagehash into venv..."
"$PIP" install boto3 imagehash -q

echo "Validating imports..."
cd "$BACKEND"
"$PYTHON" - <<'PYEOF'
import boto3; print('boto3:', boto3.__version__)
import imagehash; print('imagehash OK')
from app.services.aws_rekognition_service import rekognition_service
print('aws_rekognition_service OK, configured:', rekognition_service.is_configured)
from app.services.participant_service import ParticipantService, validate_and_decode_image
print('participant_service OK')
from app.models.participant import Participant, ParticipantImage, ParticipantPublicSource
print('participant models OK')
from app.api.v1.endpoints.participants import router
print('participants router OK')
print('')
print('ALL IMPORTS OK')
PYEOF
