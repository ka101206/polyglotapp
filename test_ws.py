import asyncio
import websockets

async def test():
    try:
        async with websockets.connect("ws://localhost:18084/ws/chat/2") as websocket:
            print("Connected!")
            await websocket.send('{"type": "ping"}')
            print("Sent ping")
            # Wait a bit
            await asyncio.sleep(1)
    except Exception as e:
        print(f"Failed: {e}")

asyncio.run(test())
