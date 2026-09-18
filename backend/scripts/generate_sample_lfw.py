"""Generate synthetic LFW-style dataset for verification and benchmarking."""
from pathlib import Path
import numpy as np
from PIL import Image

def generate():
    base = Path("data/sample_lfw")
    base.mkdir(parents=True, exist_ok=True)
    
    identities = ["Ada_Lovelace", "Alan_Turing", "Grace_Hopper"]
    for p_idx, person in enumerate(identities):
        p_dir = base / person
        p_dir.mkdir(parents=True, exist_ok=True)
        for i in range(1, 6):
            h, w = 150, 150
            arr = np.full((h, w, 3), 130 + p_idx * 15, dtype=np.uint8)
            # Face oval with identity variations
            rad_y = 50 + i * 2
            rad_x = 40 + p_idx * 3
            for r in range(h):
                for c in range(w):
                    if ((r - 75)/rad_y)**2 + ((c - 75)/rad_x)**2 < 1.0:
                        arr[r, c] = [190 + p_idx * 10, 150 + i * 5, 120 + p_idx * 8]
            # Facial details (eyes, nose, mouth)
            arr[50 + i : 60 + i, 40 : 55] = [30, 30, 30]
            arr[50 + i : 60 + i, 95 : 110] = [30, 30, 30]
            arr[68 : 83, 73:77] = [50, 40, 40]
            arr[98 + i : 108 + i, 50 : 100] = [40, 20, 20]
            # Texture with unique frequency
            freq = 0.4 + (p_idx * 5 + i) * 0.05
            noise = (np.sin(np.arange(h)[:, None] * freq) * np.cos(np.arange(w)[None, :] * freq) * 30).astype(np.int16)
            arr_textured = np.clip(arr.astype(np.int16) + noise[:, :, None], 0, 255).astype(np.uint8)
            img = Image.fromarray(arr_textured)
            img.save(p_dir / f"{person}_{i:04d}.jpg")
    print(f"Generated sample LFW dataset with {len(identities)} identities in {base}")

if __name__ == "__main__":
    generate()
