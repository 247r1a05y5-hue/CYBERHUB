#!/usr/bin/env python3
"""Package the complete repository into CYBERHUB_AWS_DATASET_FINAL.zip."""
import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZIP_OUT = ROOT / "CYBERHUB_AWS_DATASET_FINAL.zip"

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".system_generated",
    "dist",
    ".turbo",
    ".idea",
    ".vscode",
}

EXCLUDE_EXTS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log",
}

EXCLUDE_FILES = {
    "CYBERHUB_AWS_DATASET_FINAL.zip",
    "CYBERHUB_FINAL_WORKING.zip",
    "videoplayback (1).mp4",
    "videoplayback.mp4",
    "Gemini_Generated_Image_id2mzhid2mzhid2m (1).png",
    "Gemini_Generated_Image_ue4vamue4vamue4v.png",
}

def should_exclude(path: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
    if path.name in EXCLUDE_FILES:
        return True
    if path.suffix in EXCLUDE_EXTS:
        return True
    return False

print(f"Packaging CyberHub repository to {ZIP_OUT}...")
file_count = 0
total_size = 0

with zipfile.ZipFile(ZIP_OUT, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(ROOT):
        # Prune dirs
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            file_path = Path(root) / f
            if should_exclude(file_path):
                continue
            arcname = file_path.relative_to(ROOT)
            zf.write(file_path, arcname)
            file_count += 1
            total_size += file_path.stat().st_size

zip_size_mb = ZIP_OUT.stat().st_size / (1024 * 1024)
print(f"[SUCCESS] Packaged {file_count} files ({total_size / (1024*1024):.2f} MB uncompressed) into {ZIP_OUT.name} ({zip_size_mb:.2f} MB compressed).")
