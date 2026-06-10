import asyncio
from ai_client import AIClient

async def test():
    client = AIClient()
    sp = """You are a strict Japanese grammar checker.
Analyze the following sentence from a language learner: "聞きたいものをあるますです"

You MUST respond in this exact format:
Grammar Correct: [YES or NO]
Correction: [The corrected sentence, if NO. If YES, leave blank]
Explanation: [Write your explanation ENTIRELY IN ENGLISH. You are strictly forbidden from using Romaji (e.g. do NOT write "arimasu" or "ga"). Use Kana/Kanji for Japanese words, but all other words MUST be English.]"""
    
    raw = await client._complete(
        messages=[{"role": "system", "content": sp}],
        temperature=0.1,
        max_tokens=200
    )
    print(f"RESULT:\n{raw}")

asyncio.run(test())
