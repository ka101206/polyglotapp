# ai_client.py
import os
import re
from openai import AsyncOpenAI
import config

class AIClient:
    def __init__(self, model_override=None):
        vllm_url = os.environ.get("VLLM_URL", "http://localhost:8000/v1")

        if vllm_url == "openai":
            self.client = AsyncOpenAI(api_key=config.API_KEY)
            self.model = model_override or "gpt-4o-mini"
        else:
            api_key = os.environ.get("OPENAI_API_KEY", "dummy_key_for_vllm")
            self.client = AsyncOpenAI(base_url=vllm_url, api_key=api_key)
            self.model = os.environ.get("AI_MODEL", model_override or "Qwen/Qwen2.5-7B-Instruct")

        self.conversation_history = []
        self.scenario_history = []
        
        self.conversation_memory = ""
        self.scenario_memory = ""
        
        self.grammar_cache = {}
        self.word_bank_cache = {}

    # ---------- Shared helpers ----------

    # By splitting on commas as well as periods, we send smaller chunks to the TTS engine.
    # This drastically reduces the "time to first audio" latency, making the app feel much faster!
    SENTENCE_TERMINATORS = ['。', '！', '？', '.', '!', '?', '、', ',']

    def clear_history(self):
        self.conversation_history = []
        self.scenario_history = []

    def _cleanup_text(self, text):
        lines = text.split('\n')
        cleaned = [l.strip() for l in lines if any(c.isalnum() for c in l)]
        reply = " ".join(cleaned)
        reply = re.sub(r'^[。・•\-\*]\s*', '', reply)
        return reply.strip()

    async def _complete(self, messages, temperature=0.2, max_tokens=60):
        """Non-streaming completion. Returns the text content."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()

    async def _stream_sentences(self, messages, temperature=0.2, max_tokens=60):
        """Async generator that yields (text_delta, sentence_text, full_reply, success, is_done)."""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            full_reply = ""
            sentence_buf = ""

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_reply += token
                    sentence_buf += token

                    is_end = any(t in token for t in self.SENTENCE_TERMINATORS)
                    yield token, (sentence_buf if is_end else ""), full_reply, True, False
                    if is_end:
                        sentence_buf = ""

            # Flush remaining
            if sentence_buf.strip():
                yield "", sentence_buf, full_reply, True, False

            # Done signal
            yield "", "", full_reply, True, True

        except Exception as e:
            yield f"Error: {e}", "", "", False, True

    # ---------- Chat ----------

    async def get_reply_stream(self, user_text, target_language, difficulty="Intermediate"):
        system_prompt = f"""ROLE: Human text-message language partner. NOT an AI assistant. Brief, natural, conversational.

RULES:
1. Max 30 words, 1-2 sentences. No lists or essays.
2. MIRROR the user's formality exactly. Formal→formal, casual→casual. Never mix.
3. Speak ONLY in {target_language}. 100% immersion, no language mixing.
4. No violent/explicit/R-18 content.
"""
        if target_language == "Japanese":
            system_prompt += """JAPANESE RULES:
- Formal triggers (です/ます/でしょうか) → reply in 丁寧語
- Casual triggers (だ/俺/さ/よ) → reply in タメ口, zero です/ます
- No Romaji. Pure Japanese only.

EXAMPLES:
User: 相談があるんですが、いいでしょうか？ → もちろんです！どのようなご相談ですか？
User: 相談があるんだけど、いいかな？ → もちろん！何でも聞いてね。"""
        else:
            system_prompt += f"Mirror {target_language} formality conventions strictly."

        diff_rules = config.DIFFICULTY_PROMPT_MODIFIERS.get(difficulty, config.DIFFICULTY_PROMPT_MODIFIERS["Intermediate"])
        system_prompt += f"\n\n[DIFFICULTY: {difficulty}]\n{diff_rules}"

        if self.conversation_memory:
            system_prompt += f"\n\n[PREVIOUS CONTEXT SUMMARY]\n{self.conversation_memory}\n"

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": user_text})

        full = ""
        async for delta, sentence, full_reply, ok, done in self._stream_sentences(messages):
            full = full_reply
            yield delta, sentence, full_reply, ok, done
            if not ok or done:
                break

        # Save history only on success
        if full:
            self.conversation_history.append({"role": "user", "content": user_text})
            self.conversation_history.append({"role": "assistant", "content": self._cleanup_text(full)})
            
            # Trigger History Summarization
            if len(self.conversation_history) > 12:
                import asyncio
                old_messages = self.conversation_history[:6]
                self.conversation_history = self.conversation_history[6:]
                asyncio.create_task(self._summarize_history(old_messages))

    # ---------- Scenarios ----------

    def start_scenario(self, intro_text):
        self.scenario_history = [{"role": "assistant", "content": intro_text}]

    async def get_scenario_reply_stream(self, user_text, target_language, difficulty, scenario_dict):
        self.scenario_history.append({"role": "user", "content": user_text})

        handholding = (
            f"Extreme hand-holding for {difficulty} learner. Simplest vocabulary. ALL in {target_language}."
            if ("Beginner" in difficulty or "Elementary" in difficulty)
            else "Speak naturally."
        )

        system_prompt = f"""ROLE: {scenario_dict['ai_role']} in "{scenario_dict['title']}". {scenario_dict.get('persona_instruction', '')}
User is: {scenario_dict['user_role']}. Goal: {scenario_dict['goal']}

RULES:
1. Stay in character. 100% {target_language}, no English, no Romaji.
2. Max 30 words. {handholding}
3. If user FULLY achieves their goal, append "[GOAL_REACHED]" to your response. Only if goal is conclusively met.
"""
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.scenario_history)

        full = ""
        async for delta, sentence, full_reply, ok, done in self._stream_sentences(messages):
            full = full_reply
            yield delta, sentence, full_reply, ok, done
            if not ok or done:
                break

        if full:
            self.scenario_history.append({"role": "assistant", "content": self._cleanup_text(full)})
            if len(self.scenario_history) > 12:
                self.scenario_history = self.scenario_history[-12:]
        else:
            # Remove the user message we appended if it failed
            if self.scenario_history and self.scenario_history[-1].get("role") == "user":
                self.scenario_history.pop()

    async def _summarize_history(self, old_messages):
        sp = f"""You are a memory module. Summarize the following past conversation into a brief, dense bulleted list of key facts, context, and user details.
Existing Memory:
{self.conversation_memory}
Include both the existing memory and new facts from the conversation."""
        try:
            summary = await self._complete(
                [{"role": "system", "content": sp}] + old_messages,
                temperature=0.1, max_tokens=200
            )
            self.conversation_memory = summary
        except Exception as e:
            print(f"Memory summarization error: {e}")

    # ---------- Grammar ----------

    async def get_grammar_correction(self, user_text, target_language):
        cache_key = f"{target_language}:{user_text.strip().lower()}"
        if cache_key in self.grammar_cache:
            return self.grammar_cache[cache_key]

        system_prompt = f"""Strict grammar analyzer for {target_language}. Non-conversational.

RULES:
1. You are checking for hard grammar errors only.
2. If the sentence is grammatically valid and understandable—even if casual, colloquial, or simple—reply EXACTLY with the word "PERFECT". Do NOT correct for formality or style.
3. If there are real errors, give the correction + brief English explanation. No filler.
4. No Romaji/Pinyin. Native script only.

User: "おすすめの勉強方法とかある？" → PERFECT
User: "こんにちは" → PERFECT
User: "何は手伝いですますか" → Correction: 何か手伝いましょうか / "何は"+"手伝いですますか" is incorrect. Use "何か手伝いましょうか"."""
        try:
            reply = await self._complete(
                [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}],
                temperature=0.1, max_tokens=150,
            )
            lower = reply.lower()
            if any(w in lower[:15] for w in ("perfect", "correct", "no errors")):
                self.grammar_cache[cache_key] = None
                return None
            reply = re.sub(r'\s*\([a-zA-Z\s\-]+\)', '', reply)
            result = reply if reply else None
            self.grammar_cache[cache_key] = result
            return result
        except Exception:
            return None

    # ---------- Definitions ----------

    async def get_definition(self, word, context, target_language):
        import urllib.parse
        import urllib.request
        import json
        import asyncio

        def _fetch():
            try:
                safe_word = urllib.parse.quote(word)
                url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q={safe_word}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=3) as response:
                    res = json.loads(response.read().decode())
                    return res[0][0][0]
            except Exception:
                return None

        translation = await asyncio.to_thread(_fetch)
        if not translation:
            return "Definition not available."

        reading_prefix = ""
        if target_language == "Japanese":
            try:
                import pykakasi
                kks = pykakasi.kakasi()
                res = kks.convert(word)
                reading = "".join([item['hira'] for item in res])
                if reading and reading != word:
                    reading_prefix = f"Reading: {reading}\n"
            except Exception:
                pass

        return f"{reading_prefix}{word}: {translation}"

    # ---------- Word Bank ----------

    async def generate_word_bank(self, ai_reply, target_language, include_decoys=False):
        cache_key = f"{target_language}:{ai_reply.strip().lower()}:{include_decoys}"
        if cache_key in self.word_bank_cache:
            return self.word_bank_cache[cache_key], True

        count = 15 if include_decoys else 10
        sp = f"""The AI just said: "{ai_reply}".
Provide a comma-separated list of {count} words/tokens in {target_language} that the user could use to build a natural reply.
Mix nouns, verbs, particles, and punctuation. Do NOT use Romaji/Pinyin. Output ONLY the {target_language} comma-separated list, nothing else."""
        try:
            raw = await self._complete(
                [{"role": "system", "content": sp}], temperature=0.5, max_tokens=100,
            )
            if target_language == "Japanese":
                tokens = re.split(r'[,\s、]+', raw)
            else:
                tokens = re.split(r'[,\s]+', raw)
            tokens = [t.strip() for t in tokens if t.strip()]
            if len(tokens) < 3:
                res = [ch for ch in raw if ch.strip() and ch not in " \n,"]
            else:
                import random
                random.shuffle(tokens)
                res = tokens
            
            if res:
                self.word_bank_cache[cache_key] = res
            return res, True
        except Exception as e:
            print(f"Word bank error: {e}")
            return [], False

    # ---------- Grammar Tutor Chat ----------

    async def chat_with_grammar_tutor(self, user_question, original_text, grammar_correction, history, target_language):
        sp = f"""Grammar tutor for {target_language}. Student said: "{original_text}". Correction: "{grammar_correction}"
Answer questions about this correction. Brief, encouraging, easy to understand.

RULES:
1. Explain in English only. No Chinese or other languages.
2. No Romaji/Pinyin. BAD: "やあ (ya-ah)" GOOD: "やあ"
3. Be concise. Say each point once.
"""
        messages = [{"role": "system", "content": sp}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_question})
        try:
            return await self._complete(messages, temperature=0.5, max_tokens=200)
        except Exception as e:
            return f"Error connecting to tutor: {e}"

    # ---------- Stateless (grammar breakdown) ----------

    async def get_stateless_reply(self, prompt):
        sp = """[ROLE]
You are an expert language grammar tutor. 
Your job is to explain grammar, sentence structure, and vocabulary clearly and concisely in English. 
Break down the components of the sentences provided to you so a learner can easily understand them.
Feel free to use formatting like bullet points or newlines if it helps clarify the grammar."""
        try:
            reply = await self._complete(
                [{"role": "system", "content": sp}, {"role": "user", "content": prompt}],
                temperature=0.2, max_tokens=300,
            )
            return reply, True
        except Exception as e:
            return f"Error: {e}", False
