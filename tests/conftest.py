import os

# Disable Opik tracing during tests to avoid sending data and needing API keys
os.environ.setdefault("OPIK_TRACK_DISABLE", "true")
