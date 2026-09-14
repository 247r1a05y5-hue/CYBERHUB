import sys
try:
    import google.auth
    from google.cloud import vision
    print("GOOGLE_LIBS_INSTALLED=TRUE")
    credentials, project = google.auth.default()
    print(f"AUTH_SUCCESS=TRUE PROJECT={project}")
except Exception as e:
    print(f"AUTH_ERROR: {e}")
