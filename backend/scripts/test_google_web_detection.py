#!/usr/bin/env python3
"""Diagnostic script for testing Google Cloud Vision Web Detection with real live API."""
import os
import sys
import io
from PIL import Image, ImageDraw

try:
    import google.auth
    from google.cloud import vision
except ImportError as e:
    print(f"FAILED: Google Cloud Vision client library not installed: {e}")
    sys.exit(1)

def create_test_image_bytes() -> bytes:
    """Create a distinct test image."""
    img = Image.new("RGB", (256, 256), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((20, 20), "CYBERHUB Live Vision Test", fill=(255, 255, 0))
    d.rectangle([(40, 40), (200, 200)], outline=(255, 0, 0), width=3)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def main():
    print("--- 1. Authenticating via ADC ---")
    try:
        credentials, project = google.auth.default()
        print(f"ADC Auth Success! Default Project: {project}")
    except Exception as e:
        print(f"ADC Auth Failed: {e}")
        sys.exit(1)

    print("\n--- 2. Initializing Vision ImageAnnotatorClient ---")
    try:
        client = vision.ImageAnnotatorClient()
        print("ImageAnnotatorClient initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize client: {e}")
        sys.exit(1)

    print("\n--- 3. Preparing Image & Web Detection Request ---")
    # Check if there is an existing test reference image on disk, else create one
    image_bytes = create_test_image_bytes()
    image = vision.Image(content=image_bytes)

    print("\n--- 4. Sending live Web Detection Request to GCP ---")
    try:
        response = client.web_detection(image=image, max_results=10)
        if response.error.message:
            print(f"Vision API returned error in response: {response.error.message}")
            sys.exit(1)
        
        web_detection = response.web_detection
        print("\n--- 5. LIVE VISION API RESPONSE RECEIVED SUCCESSFULLY! ---")
        
        # Parse fields
        full_matches = [img.url for img in web_detection.full_matching_images]
        partial_matches = [img.url for img in web_detection.partial_matching_images]
        pages = [(p.url, p.page_title) for p in web_detection.pages_with_matching_images]
        similar_images = [img.url for img in web_detection.visually_similar_images]
        entities = [(e.description, e.score) for e in web_detection.web_entities if e.description]
        best_guess = [b.label for b in web_detection.best_guess_labels]

        print(f"Full Matches: {len(full_matches)}")
        print(f"Partial Matches: {len(partial_matches)}")
        print(f"Pages with Matches: {len(pages)}")
        print(f"Visually Similar Images: {len(similar_images)}")
        print(f"Web Entities: {len(entities)}")
        print(f"Best Guess Labels: {best_guess}")

        print("\nSUMMARY:")
        print("GOOGLE VISION:          PASS")
        print("AUTHENTICATION:         PASS")
        print("WEB_DETECTION:          PASS")
        print("REAL_RESULT_RECEIVED:   YES")

    except Exception as e:
        print(f"Live Vision API Call Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
