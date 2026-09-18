import sys
print("Python version:", sys.version)
packages = ["numpy", "cv2", "PIL", "onnxruntime", "torch", "torchvision", "imagehash", "boto3", "qdrant_client", "scipy"]
for pkg in packages:
    try:
        m = __import__(pkg)
        print(f"{pkg}:", getattr(m, "__version__", "installed"))
    except ImportError:
        print(f"{pkg}: NOT INSTALLED")
