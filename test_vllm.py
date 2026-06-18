import asyncio
from ai_client import AIClient
async def test():
    c = AIClient()
    reply = await c.chat("Hola", "Spanish", "Beginner", "なし", "")
    print(reply)
asyncio.run(test())
