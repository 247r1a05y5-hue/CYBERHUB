"""Image Analysis Pipeline — Hashes, Quality Indicators & Safe Metadata.

Calculates:
- Cryptographic SHA-256 digest
- Perceptual hashes (pHash - DCT, dHash - gradient difference)
- Quality indicators (Sharpness/Laplacian, Brightness, Contrast, Entropy)
- Safe metadata extraction with data minimization
"""
from __future__ import annotations

import hashlib
import io
import math
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageOps, ImageStat


@dataclass(frozen=True)
class ImageQualityMetrics:
    """Quantitative quality indicators."""
    brightness: float  # Mean luminance (0.0 to 100.0)
    contrast: float    # Contrast std dev (0.0 to 100.0)
    sharpness: float   # Sharpness score (Laplacian approximation variance)
    entropy: float     # Shannon entropy (0.0 to 8.0)
    is_usable: bool    # Overall quality usability threshold


@dataclass(frozen=True)
class ImageAnalysisResult:
    """Full analysis output for reference and discovered images."""
    sha256_hash: str
    phash: str
    dhash: str
    width: int
    height: int
    format: str
    color_mode: str
    quality: ImageQualityMetrics
    safe_metadata: dict[str, Any]


class ImageAnalysisService:
    """Computes hashes, quality indicators, and safe metadata for image instances."""

    @staticmethod
    def compute_sha256(file_bytes: bytes) -> str:
        """Compute SHA-256 digest."""
        return hashlib.sha256(file_bytes).hexdigest()

    @staticmethod
    def compute_dhash(image: Image.Image, hash_size: int = 8) -> str:
        """Compute Difference Hash (dHash) using horizontal gradient.
        
        Resizes to (hash_size + 1, hash_size), converts to grayscale,
        and computes adjacent pixel difference bits.
        """
        resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = list(resized.getdata())

        difference = []
        for row in range(hash_size):
            row_start = row * (hash_size + 1)
            for col in range(hash_size):
                pixel_left = pixels[row_start + col]
                pixel_right = pixels[row_start + col + 1]
                difference.append(pixel_left > pixel_right)

        # Convert boolean list to hexadecimal string
        decimal_val = 0
        hex_string = []
        for idx, val in enumerate(difference):
            if val:
                decimal_val += 2 ** (idx % 4)
            if (idx % 4) == 3:
                hex_string.append(f"{decimal_val:x}")
                decimal_val = 0
        return "".join(hex_string)

    @staticmethod
    def compute_phash(image: Image.Image, hash_size: int = 8, highfreq_factor: int = 4) -> str:
        """Compute Perceptual Hash (pHash) using discrete cosine transform principles.
        
        Resizes to (hash_size * 4, hash_size * 4), applies 2D DCT,
        takes top-left 8x8 AC coefficients, and computes median threshold bits.
        """
        img_size = hash_size * highfreq_factor
        resized = image.convert("L").resize((img_size, img_size), Image.Resampling.LANCZOS)
        pixels = list(resized.getdata())

        # Convert to 2D matrix
        matrix = [
            pixels[i * img_size : (i + 1) * img_size]
            for i in range(img_size)
        ]

        # 2D DCT calculation
        def dct_1d(vector: list[float]) -> list[float]:
            n = len(vector)
            result = []
            for u in range(n):
                sum_val = 0.0
                alpha = math.sqrt(1.0 / n) if u == 0 else math.sqrt(2.0 / n)
                for x in range(n):
                    sum_val += vector[x] * math.cos((2 * x + 1) * u * math.pi / (2.0 * n))
                result.append(alpha * sum_val)
            return result

        # Apply DCT along rows then cols
        dct_rows = [dct_1d([float(val) for val in row]) for row in matrix]
        dct_matrix = [[0.0] * img_size for _ in range(img_size)]
        for col in range(img_size):
            col_vector = [dct_rows[row][col] for row in range(img_size)]
            dct_col = dct_1d(col_vector)
            for row in range(img_size):
                dct_matrix[row][col] = dct_col[row]

        # Extract top-left 8x8 coefficients (excluding DC at [0,0])
        submatrix = [
            dct_matrix[r][c]
            for r in range(hash_size)
            for c in range(hash_size)
        ]
        # Calculate median of low-frequency AC components
        ac_coeffs = submatrix[1:]  # Exclude DC
        if not ac_coeffs:
            med = 0.0
        else:
            sorted_ac = sorted(ac_coeffs)
            med = sorted_ac[len(sorted_ac) // 2]

        # Construct hash
        diff = [1 if val > med else 0 for val in submatrix]
        hex_parts = []
        for i in range(0, len(diff), 4):
            chunk = diff[i : i + 4]
            val = sum(bit * (2 ** (3 - j)) for j, bit in enumerate(chunk))
            hex_parts.append(f"{val:x}")
        return "".join(hex_parts)

    @staticmethod
    def calculate_hamming_distance(hash1: str, hash2: str) -> int:
        """Calculate bitwise Hamming distance between two hex hashes."""
        if len(hash1) != len(hash2):
            # Pad to equal length
            max_len = max(len(hash1), len(hash2))
            hash1 = hash1.zfill(max_len)
            hash2 = hash2.zfill(max_len)

        try:
            int1 = int(hash1, 16)
            int2 = int(hash2, 16)
            return bin(int1 ^ int2).count("1")
        except ValueError:
            return 64  # Max distance on error

    @classmethod
    def calculate_quality(cls, image: Image.Image) -> ImageQualityMetrics:
        """Calculate brightness, contrast, sharpness, and entropy."""
        grayscale = image.convert("L")
        stat = ImageStat.Stat(grayscale)

        # Brightness (mean: 0..255 -> 0..100)
        mean_lum = stat.mean[0]
        brightness_pct = (mean_lum / 255.0) * 100.0

        # Contrast (std dev: 0..128 -> 0..100)
        std_dev = stat.stddev[0]
        contrast_pct = min(100.0, (std_dev / 128.0) * 100.0)

        # Sharpness via Laplacian 3x3 kernel variance approximation
        w, h = grayscale.size
        # Sample center region for performance
        crop_box = (
            int(w * 0.1),
            int(h * 0.1),
            int(w * 0.9),
            int(h * 0.9),
        )
        cropped = grayscale.crop(crop_box).resize((128, 128), Image.Resampling.BOX)
        pixels = list(cropped.getdata())
        cw, ch = 128, 128

        laplacian_vals = []
        for y in range(1, ch - 1):
            for x in range(1, cw - 1):
                center = pixels[y * cw + x]
                up = pixels[(y - 1) * cw + x]
                down = pixels[(y + 1) * cw + x]
                left = pixels[y * cw + (x - 1)]
                right = pixels[y * cw + (x + 1)]
                lap = 4 * center - up - down - left - right
                laplacian_vals.append(lap)

        if laplacian_vals:
            lap_mean = sum(laplacian_vals) / len(laplacian_vals)
            lap_var = sum((v - lap_mean) ** 2 for v in laplacian_vals) / len(laplacian_vals)
            sharpness_score = round(min(100.0, lap_var / 15.0), 2)
        else:
            sharpness_score = 0.0

        # Shannon Entropy (0.0 to 8.0)
        hist = grayscale.histogram()
        total_pixels = float(sum(hist))
        entropy = 0.0
        if total_pixels > 0:
            for count in hist:
                if count > 0:
                    p = count / total_pixels
                    entropy -= p * math.log2(p)
        entropy_score = round(entropy, 2)

        # Usability check (not pitch black, not solid white, sufficient contrast)
        is_usable = (
            10.0 <= brightness_pct <= 95.0
            and contrast_pct >= 8.0
            and sharpness_score >= 1.0
        )

        return ImageQualityMetrics(
            brightness=round(brightness_pct, 2),
            contrast=round(contrast_pct, 2),
            sharpness=sharpness_score,
            entropy=entropy_score,
            is_usable=is_usable,
        )

    @classmethod
    def analyze(cls, file_bytes: bytes) -> ImageAnalysisResult:
        """Run full analysis pipeline on image bytes."""
        sha256 = cls.compute_sha256(file_bytes)

        with Image.open(io.BytesIO(file_bytes)) as img:
            width, height = img.size
            img_format = img.format or "UNKNOWN"
            color_mode = img.mode

            phash = cls.compute_phash(img)
            dhash = cls.compute_dhash(img)
            quality = cls.calculate_quality(img)

            # Safe metadata (data minimization — no personal EXIF or GPS)
            has_exif = bool(getattr(img, "_getexif", None) and img._getexif())
            safe_meta = {
                "width": width,
                "height": height,
                "aspect_ratio": round(width / max(1, height), 3),
                "format": img_format,
                "color_mode": color_mode,
                "has_exif_tags": has_exif,
                "megapixels": round((width * height) / 1_000_000, 2),
            }

        return ImageAnalysisResult(
            sha256_hash=sha256,
            phash=phash,
            dhash=dhash,
            width=width,
            height=height,
            format=img_format,
            color_mode=color_mode,
            quality=quality,
            safe_metadata=safe_meta,
        )

    # Backward-compatibility alias used by unit tests
    analyze_image = analyze


image_analysis_service = ImageAnalysisService()
