"""Download and extract official InsightFace buffalo_l model pack."""
import io
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

def download_buffalo_l():
    target_dir = Path("models/insightface/buffalo_l")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    expected_files = ["w600k_r50.onnx", "det_10g.onnx", "2d106det.onnx", "1k3d68.onnx", "genderage.onnx"]
    if all((target_dir / f).exists() for f in ["w600k_r50.onnx"]):
        print(f"buffalo_l models already exist at {target_dir.resolve()}")
        for f in target_dir.iterdir():
            print(f"  - {f.name} ({f.stat().st_size / (1024*1024):.2f} MB)")
        return

    url = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
    print(f"Downloading official InsightFace buffalo_l pack from {url}...")
    
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    
    with urllib.request.urlopen(req) as resp:
        content_len = resp.headers.get("Content-Length")
        if content_len:
            print(f"Total size: {int(content_len)/(1024*1024):.2f} MB")
        zip_bytes = resp.read()
        print(f"Downloaded {len(zip_bytes)/(1024*1024):.2f} MB. Extracting to {target_dir.resolve()}...")
        
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            z.extractall(target_dir)
            
    print("Extracted files:")
    for f in target_dir.iterdir():
        print(f"  - {f.name} ({f.stat().st_size / (1024*1024):.2f} MB)")

if __name__ == "__main__":
    download_buffalo_l()
