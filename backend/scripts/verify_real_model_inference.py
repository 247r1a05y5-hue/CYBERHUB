"""Verification test for InsightFace buffalo_l / w600k_r50.onnx model on real LFW image."""
import hashlib
import math
from pathlib import Path
import numpy as np
from PIL import Image

from app.services.face_detection_service import FaceDetectionService
from app.services.face_embedding_service import FaceEmbeddingService

def verify():
    print("=" * 70)
    print("INSIGHTFACE REAL MODEL & INFERENCE VERIFICATION")
    print("=" * 70)
    
    svc = FaceEmbeddingService()
    model_path = svc.model_path
    
    print(f"Model Family:             {svc.model_family}")
    print(f"Model Pack:               {svc.model_pack}")
    print(f"Recognition Model:        {svc.model_name}")
    print(f"Model Version:            {svc.model_version}")
    print(f"Embedding Dimension:      {svc.embedding_dimension}")
    print(f"Model Path:               {model_path.resolve()}")
    
    if not model_path.exists():
        print(f"FATAL: Model file not found at {model_path}")
        return False
        
    file_size_mb = model_path.stat().st_size / (1024 * 1024)
    print(f"File Size:                {file_size_mb:.2f} MB")
    
    sha256 = svc.model_sha256
    print(f"SHA-256 Checksum:         {sha256}")
    
    # Load ONNX Session
    session = svc._ensure_session()
    inputs = session.get_inputs()
    outputs = session.get_outputs()
    
    print(f"ONNX Input Name:          {inputs[0].name} (Shape: {inputs[0].shape}, Type: {inputs[0].type})")
    print(f"ONNX Output Name:         {outputs[0].name} (Shape: {outputs[0].shape}, Type: {outputs[0].type})")
    print(f"Session Providers:        {session.get_providers()}")
    
    # Locate one real image from LFW
    lfw_root = Path("data/lfw/identities") if Path("data/lfw/identities").exists() else Path("data/lfw")
    real_images = list(lfw_root.glob("*/*.jpg"))
    if not real_images:
        print("ERROR: No real LFW test images found.")
        return False
        
    test_img_path = real_images[0]
    print(f"\nTesting real inference on: {test_img_path}")
    raw_bytes = test_img_path.read_bytes()
    
    detector = FaceDetectionService()
    det = detector.detect_and_validate(raw_bytes)
    print(f"Detection Status:         {det.status.value} (Face Count: {det.face_count})")
    if det.primary_face:
        print(f"Quality Metrics:          Sharpness={det.primary_face.quality.sharpness}, Brightness={det.primary_face.quality.brightness}, Contrast={det.primary_face.quality.contrast}")
        
    emb = svc.embed(raw_bytes)
    emb_arr = np.array(emb, dtype=np.float32)
    l2_norm = float(np.linalg.norm(emb_arr))
    
    print(f"Returned Vector Dim:      {len(emb)}")
    print(f"Vector L2 Norm:           {l2_norm:.6f}")
    print(f"Sample Embedding Chunk:   {emb[:5]}...")
    
    assert len(emb) == 512, f"Expected 512-d, got {len(emb)}"
    assert abs(l2_norm - 1.0) < 1e-3, f"Expected unit norm 1.0, got {l2_norm}"
    
    print("\nVERIFICATION RESULT:      SUCCESS (Real Model Inference Operational)")
    print("=" * 70)
    return True

if __name__ == "__main__":
    verify()
