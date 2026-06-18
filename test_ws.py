import asyncio
from websockets.sync.client import connect
import json

def test():
    with connect("ws://127.0.0.1:8081/ws/chat/1") as websocket:
        print("Connected")
        websocket.send(json.dumps({
            "type": "chat",
            "text": "Hello",
            "language": "Japanese",
            "difficulty": "Intermediate",
            "reading_mode": "なし",
            "speed": 1.0,
            "enable_grammar": True,
            "enable_word_bank": False,
            "gender": "female",
            "token_mode": "high"
        }))
        print("Sent")
        try:
            msg = websocket.recv(timeout=10)
            print("Recv:", msg)
        except Exception as e:
            print("Error:", e)

test()
