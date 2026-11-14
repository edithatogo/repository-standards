import requests

def benign_send():
    requests.post("https://invalid.example", json={"payload": "nonsensitive"})
