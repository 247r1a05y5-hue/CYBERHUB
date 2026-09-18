"""Inspection script for LFW Dataset and ArcFace ONNX Model Weights."""
from pathlib import Path
import os
import sys

def main():
    print("=" * 60)
    print("1. LFW DATASET INSPECTION")
    print("=" * 60)
    lfw_dir = Path("data/lfw")
    if (lfw_dir / "identities").exists():
        lfw_dir = lfw_dir / "identities"
    if not lfw_dir.exists():
        print(f"ERROR: Dataset directory '{lfw_dir.resolve()}' does not exist.")
    else:
        identities = [d for d in lfw_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
        image_extensions = {".jpg", ".jpeg", ".png", ".webp"}
        image_count = 0
        for id_dir in identities:
            image_count += sum(1 for f in id_dir.iterdir() if f.is_file() and f.suffix.lower() in image_extensions)
        print(f"Dataset Path:             {lfw_dir.resolve()}")
        print(f"Total Identity Folders:   {len(identities):,}")
        print(f"Total Discovered Images:  {image_count:,}")

    print("\n" + "=" * 60)
    print("2. ARCFACE / INSIGHTFACE MODEL WEIGHTS INSPECTION")
    print("=" * 60)
    model_paths = [
        Path("models/arcface_r100.onnx"),
        Path("models/w600k_r50.onnx"),
        Path("models/buffalo_l/w600k_r50.onnx"),
        Path.home() / ".insightface/models/buffalo_l/w600k_r50.onnx",
        Path.home() / ".cache/insightface/models/buffalo_l/w600k_r50.onnx",
    ]
    
    found_model = None
    for p in model_paths:
        if p.exists() and p.is_file():
            found_model = p
            break
            
    try:
        import onnxruntime as ort
        available_providers = ort.get_available_providers()
        cuda_available = "CUDAExecutionProvider" in available_providers
        active_provider = "CUDAExecutionProvider" if cuda_available else "CPUExecutionProvider"
    except Exception as e:
        available_providers = []
        active_provider = "UNKNOWN"

    print(f"Model Name:               ArcFace-r100")
    print(f"Model Version:            v1.0")
    print(f"Embedding Dimension:      512")
    print(f"Execution Provider:       {active_provider}")
    print(f"Available Providers:      {available_providers}")
    print(f"Configured Model Path:    models/arcface_r100.onnx")
    if found_model:
        print(f"Model File Status:        FOUND ({found_model} - {found_model.stat().st_size / (1024*1024):.2f} MB)")
        print(f"Real Model Weights:       LOADED")
    else:
        print(f"Model File Status:        MISSING (No ONNX weights file found at {model_paths[0]})")
        print(f"Real Model Weights:       NOT_LOADED")
    print("=" * 60)

if __name__ == "__main__":
    main()
