import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        req = {
            "model": "qwen3.6-35b-a3b",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "[REGISTER: FORMAL] こんにちは"}
            ],
            "max_tokens": 1000
        }
        resp = await client.post(
            "http://localhost:8001/v1/chat/completions",
            json=req,
            timeout=120.0
        )
        print(resp.json()['choices'][0]['message']['content'])

asyncio.run(main())
