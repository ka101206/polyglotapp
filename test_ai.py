import asyncio
from dotenv import load_dotenv
load_dotenv()
from ai_client import AIClient

async def test():
    client = AIClient()
    print("Sending message...")
    generator = client.get_reply_stream("こんにちは、調子はどうですか？", "Japanese", "Intermediate", enable_grammar=True, enable_word_bank=True)
    
    async for delta, sentence, full_reply, ok, done, extras in generator:
        if delta:
            print(f"DELTA: {delta}", end="", flush=True)
        if done:
            print("\nDONE!")
            print(f"FULL REPLY: {full_reply}")
            print(f"EXTRAS: {extras}")

if __name__ == "__main__":
    asyncio.run(test())
