"""Display current ingestion checkpoint status."""
import json
from pathlib import Path

p = Path("data/lfw_full_ingestion_checkpoint.json")
if not p.exists():
    print("Checkpoint file not found.")
else:
    with open(p) as f:
        data = json.load(f)
    summary = {k: v for k, v in data.items() if k != "processed_hashes"}
    print(json.dumps(summary, indent=2))
