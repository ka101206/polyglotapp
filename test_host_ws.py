import asyncio
from websockets.sync.client import connect

def test():
    try:
        with connect("ws://10.74.10.244:18084/ws/chat/1") as websocket:
            print("Connected")
    except Exception as e:
        print("Error:", e)

test()
