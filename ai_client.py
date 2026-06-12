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
            self.model = os.environ.get("AI_MODEL", model_override or "Qwen/Qwen3.5-9B")

        self.conversation_history = []
        self.scenario_history = []
        
        self.conversation_memory = ""
        self.scenario_memory = ""
        
        self.current_register = "FORMAL"
        
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
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        text = re.sub(r'(?is)Here\'s a thinking process.*?</think>', '', text)
        text = re.sub(r'(?is)Here\'s a thinking process.*?✅\s*', '', text)
        text = re.sub(r'(?is)Here\'s a thinking process.*?(?=(?:こんにちは|承知|分かり|はい|いいえ|もちろん|そうですね|よろしく|初めまして|[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]))', '', text)
        # Catch any lines starting with numbers, bullet points, or English reasoning phrases
        lines = text.split('\n')
        cleaned = []
        in_reasoning = True
        for l in lines:
            if not l.strip():
                continue
            
            # If we see Japanese characters, we've likely hit the actual reply
            if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', l):
                in_reasoning = False
            
            if not in_reasoning:
                cleaned.append(l.strip())
            elif not re.match(r'^[\d\.\-\*]|Here\'s|Analyze|Identify|Determine|Draft|Final Check|Checking', l.strip()):
                # Sometimes a line might not match our exact heuristic but is still part of the reply
                cleaned.append(l.strip())

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
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        return response.choices[0].message.content.strip()

    async def _stream_sentences(self, messages, temperature=0.2, max_tokens=150):
        """Async generator that yields (text_delta, sentence_text, full_reply, success, is_done, extras)."""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )

            full_text = ""
            yielded_len = 0
            sentence_buf = ""
            safe_reply = ""

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_text += token

                    reply_part = full_text
                    safe_reply = self._cleanup_text(reply_part)
                    
                    last_bracket = safe_reply.rfind("[")
                    if last_bracket != -1 and safe_reply.find("]", last_bracket) == -1:
                        safe_reply = safe_reply[:last_bracket]
                        
                    safe_reply = safe_reply.lstrip()
                    
                    if len(safe_reply) > yielded_len:
                        new_delta = safe_reply[yielded_len:]
                        yielded_len = len(safe_reply)
                        
                        sentence_buf += new_delta
                        is_end = any(t in new_delta for t in self.SENTENCE_TERMINATORS)
                        
                        yield new_delta, (sentence_buf if is_end else ""), safe_reply, True, False, {}
                        if is_end:
                            sentence_buf = ""

            # Flush remaining
            if sentence_buf.strip():
                yield "", sentence_buf, safe_reply, True, False, {}

            # Parse extras at the end
            extras = {"goal_reached": False}
            if re.search(r'\[GOAL_REACHED\]', full_text, re.IGNORECASE):
                extras["goal_reached"] = True

            # Done signal
            yield "", "", safe_reply, True, True, extras

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"Error: {e}", "", "", False, True, {}

    # ---------- Formality Detection ----------

    def _detect_formality(self, text, language):
        """Programmatically detect if user's text is formal or casual."""
        text = text.strip()
        if not text:
            return None  # can't determine

        if language == "Japanese":
            # Formal indicators: です, ます, ください, でしょう, ございます
            formal_patterns = [r'です[。？?！!、\s]*$', r'ます[。？?！!、\s]*$', r'ません', r'ました', r'ください', r'でしょう', r'ございます']
            for p in formal_patterns:
                if re.search(p, text):
                    return "FORMAL"
            # If text is just a greeting like こんにちは, treat as neutral
            if text in ('こんにちは', 'おはよう', 'こんばんは', 'やあ', 'よう'):
                return None
            # Everything else = casual (plain form verbs, だ, etc.)
            if len(text) >= 2:
                return "CASUAL"

        elif language == "Korean":
            # Formal indicators: 요, 습니다, 세요, ㅂ니다
            if re.search(r'[요세][\s。？?！!]*$', text) or '습니다' in text or 'ㅂ니다' in text:
                return "FORMAL"
            # Neutral greetings
            if text in ('안녕하세요',):
                return "FORMAL"
            if text in ('안녕',):
                return "CASUAL"
            # Everything without 요 ending = casual
            if len(text) >= 2:
                return "CASUAL"

        elif language == "Chinese":
            if '您' in text:
                return "FORMAL"
            if '你' in text:
                return "CASUAL"

        return None

    # ---------- Chat ----------

    async def get_reply_stream(self, user_text, target_language, difficulty="Intermediate", enable_grammar=True, enable_word_bank=True, user_name=None, notebook_words=None):
        # Detect and track formality register
        # Reset register if language changed
        last_lang = getattr(self, '_last_language', None)
        if last_lang and last_lang != target_language:
            self.current_register = "FORMAL"
        self._last_language = target_language

        detected = self._detect_formality(user_text, target_language)
        if detected:
            self.current_register = detected

        register = self.current_register

        # --- Build system prompt ---
        lang_rules = {
            "Japanese": {
                "script": "Japanese script only (漢字・ひらがな・カタカナ). No Romaji. No Chinese Hanzi (use 聞く not 听).",
                "CASUAL": "Reply in タメ口 (plain form). No です/ます/ください/でしょうか/ございます. Use だ/だよ/よ/ね/かな/じゃん and plain verbs.",
                "FORMAL": "Reply in 丁寧語 (です/ます form). Polite but natural, not stiff.",
            },
            "Korean": {
                "script": "Hangul only. No English. No romanization.",
                "CASUAL": "Reply in 반말. No 요/세요/습니다/ㅂ니다. Use 해/어/아/야/지/는데/거든/잖아.",
                "FORMAL": "Reply in 해요체 (요 endings). Polite but warm.",
            },
            "Chinese": {
                "script": "Simplified Chinese only. No Pinyin. No English. No Japanese characters.",
                "CASUAL": "Use 你 (casual). Do not use 您.",
                "FORMAL": "Use 您 (polite).",
            },
        }

        lang = lang_rules.get(target_language, {
            "script": f"Native {target_language} script only. No English. No transliterations.",
            "CASUAL": "Use casual/informal register.",
            "FORMAL": "Use polite/formal register.",
        })

        system_prompt = f"""You are a native {target_language} speaker texting with a friend. This is a casual chat, not a lesson.

How to reply:
- Respond to what the user said. Acknowledge their message before adding anything new.
- Keep it short: 1-2 sentences, under 30 words. Text like a real person, not a textbook.
- Mix it up: react, agree, joke, share a thought, or ask something — but don't interrogate. Not every message needs a question.
- If the user is brief, be brief back. Match their energy.
- Avoid controversial, politically sensitive, or heavy topics (war, religion, politics, tragedy). Especially avoid topics that are culturally sensitive for {target_language} speakers. Keep things light and friendly.

Register: {register} — {lang[register]}
Script: {lang['script']}
Write ONLY in {target_language}. Zero English words in your reply."""

        diff_rules = config.DIFFICULTY_PROMPT_MODIFIERS.get(difficulty, config.DIFFICULTY_PROMPT_MODIFIERS["Intermediate"])
        system_prompt += f"\nDifficulty: {difficulty}. {diff_rules}"

        if user_name:
            system_prompt += f"\nThe user's name is \"{user_name}\" — write it exactly as shown when you use it. Only use it rarely (every few messages). Don't ask their name."

        if self.conversation_memory:
            system_prompt += f"\n\n[Previous context]\n{self.conversation_memory}"

        # Anti-circular: when conversation is long enough, nudge towards notebook topics
        if len(self.conversation_history) >= 8:
            system_prompt += "\n\nThe conversation may be getting repetitive. If it feels circular (e.g. just agreeing or complimenting back and forth), naturally steer to a new topic."
            if notebook_words:
                topics_str = ", ".join(notebook_words[:15])
                system_prompt += f" The user is studying these words: [{topics_str}]. Try to bring up a topic related to these interests."

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": user_text})

        # --- TEMP DEBUG ---
        print(f"[DEBUG] User said: {user_text}", flush=True)
        print(f"[DEBUG] Register: {register} | History length: {len(self.conversation_history)}", flush=True)
        for i, m in enumerate(messages):
            role = m['role']
            content = m['content'][:120] if role == 'system' else m['content']
            print(f"[DEBUG]   msg[{i}] {role}: {content}", flush=True)
        # --- END TEMP DEBUG ---

        full = ""
        async for delta, sentence, full_reply, ok, done, extras in self._stream_sentences(messages, temperature=0.5):
            full = full_reply
            
            if done and ok:
                self.conversation_history.append({"role": "user", "content": user_text})
                self.conversation_history.append({"role": "assistant", "content": self._cleanup_text(full)})
                
                # Sliding Window History
                if len(self.conversation_history) > 12:
                    self.conversation_history = self.conversation_history[-12:]
                    
            yield delta, sentence, full_reply, ok, done, extras
            if not ok or done:
                break

    # ---------- Scenarios ----------

    def start_scenario(self, intro_text):
        self.scenario_history = [{"role": "assistant", "content": intro_text}]

    async def get_scenario_reply_stream(self, user_text, target_language, difficulty, scenario_dict, enable_grammar=True, enable_word_bank=True, user_name=None):
        self.scenario_history.append({"role": "user", "content": user_text})

        handholding = (
            f"Extreme hand-holding for {difficulty} learner. Simplest vocabulary. ALL in {target_language}."
            if ("Beginner" in difficulty or "Elementary" in difficulty)
            else "Speak naturally."
        )

        system_prompt = f"""ROLE: {scenario_dict['ai_role']} in "{scenario_dict['title']}". {scenario_dict.get('persona_instruction', '')}
User is: {scenario_dict['user_role']}. Goal: {scenario_dict['goal']}

RULES:
1. Stay in character.
2. FORMALITY: Default to polite register. If the user speaks casually (e.g. plain-form verbs, no です/ます, 반말, etc.), match their casual tone immediately.
3. ABSOLUTE LANGUAGE RULE: Speak 100% ONLY in {target_language}. NO Romaji. NO Pinyin. NO English (except acronyms like OK). Write ONLY in the native script of {target_language}. For Japanese: no Chinese Hanzi—use only Japanese Kanji.
4. Max 30 words. {handholding}
5. If user FULLY achieves their goal, append "[GOAL_REACHED]" to your response. Only if goal is conclusively met.
6. Do NOT ask the user for their name."""

        if user_name:
            system_prompt += f"\n\n[USER INFO]\nThe user's name is: {user_name}\nCRITICAL: Output this name EXACTLY as written above — same characters, same script, no changes. Do NOT romanize it, do NOT transliterate it, do NOT convert it to another writing system, do NOT re-spell it. Write \"{user_name}\" verbatim every time you address the user. Do NOT ask the user what their name is."

        system_prompt += """

CRITICAL OUTPUT FORMATTING:
Output ONLY your conversational reply. DO NOT output any thinking process, analysis, meta-commentary, or prefixes like 'Here is a thinking process' or 'Analyze User Input'. Just output the raw conversational reply text directly, with no surrounding quotes or markdown."""

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.scenario_history)

        full = ""
        async for delta, sentence, full_reply, ok, done, extras in self._stream_sentences(messages):
            full = full_reply
            
            if done and ok:
                self.scenario_history.append({"role": "assistant", "content": self._cleanup_text(full)})
                if len(self.scenario_history) > 12:
                    self.scenario_history = self.scenario_history[-12:]
            
            yield delta, sentence, full_reply, ok, done, extras
            if not ok or done:
                break

        if not full:
            if self.scenario_history and self.scenario_history[-1].get("role") == "user":
                self.scenario_history.pop()



    # ---------- Grammar ----------

    async def get_grammar_correction(self, user_text, target_language):
        cache_key = f"{target_language}:{user_text.strip().lower()}"
        if cache_key in self.grammar_cache:
            return self.grammar_cache[cache_key]

        lang_script_rule = ""
        if target_language == "Japanese":
            lang_script_rule = "Use ONLY Japanese Kanji/Kana. NEVER use Chinese Hanzi (e.g. 听 is WRONG, 聞く is correct). No Romaji."
        elif target_language == "Chinese":
            lang_script_rule = "Use ONLY Simplified Chinese characters. No Pinyin."
        elif target_language == "Korean":
            lang_script_rule = "Use ONLY Hangul. No romanization."
        else:
            lang_script_rule = f"Use only native {target_language} script."

        system_prompt = f"""Strict grammar analyzer for {target_language}. Non-conversational.

RULES:
1. You are checking for HARD STRUCTURAL GRAMMAR ERRORS ONLY.
2. DO NOT correct any of the following—these are NOT errors:
   - Casual/informal speech (e.g. タメ口, plain form, slang)
   - Formality level choices (casual vs polite is the user's choice)
   - Simple greetings or exclamations (こんにちは, 안녕, 你好, etc.)
   - Sentence fragments that are natural in conversation
   - Style preferences
3. If the sentence is grammatically valid and understandable—even if casual, colloquial, fragmented, or simple—reply EXACTLY with the word "PERFECT".
4. If there IS a real structural error (wrong particle, incorrect conjugation, impossible word order), give the correction + brief English explanation.
5. {lang_script_rule}
6. Write explanations in English. Use {target_language} script for {target_language} words only.

EXAMPLES:
User: "こんにちは" → PERFECT
User: "聞きたい事があるんだけどいいかな" → PERFECT
User: "タメ口でいいよ" → PERFECT
User: "おすすめの勉強方法とかある？" → PERFECT
User: "何は手伝いですますか" → Correction: 何か手伝いましょうか / Wrong particle: は should be か. Incorrect verb form: ですます is not valid. Use ましょうか.
User: "你好" → PERFECT
User: "안녕하세요" → PERFECT"""
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

    async def generate_word_bank(self, reply_text, target_language, include_decoys=False):
        cache_key = f"{target_language}:{reply_text.strip().lower()}:{include_decoys}"
        if cache_key in self.word_bank_cache:
            return self.word_bank_cache[cache_key], True

        count = 15 if include_decoys else 10
        sp = f"""You are a helpful language tutor.
Provide exactly {count} useful vocabulary words in {target_language} (NO CHINESE HANZI, NO ENGLISH) that the user could use to reply.
Mix nouns, verbs, particles, and punctuation. Do NOT use Romaji/Pinyin. Output ONLY the {target_language} comma-separated list, nothing else."""
        user_msg = f"Based on this text from the AI: '{reply_text}'"
        try:
            raw = await self._complete(
                [{"role": "system", "content": sp}, {"role": "user", "content": user_msg}], temperature=0.5, max_tokens=100,
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

    async def analyze_grammar(self, user_text, target_language, difficulty):
        cache_key = f"grammar:{target_language}:{user_text.strip().lower()}"
        if cache_key in self.word_bank_cache:
            return self.word_bank_cache[cache_key], True

        lang_script_rule = ""
        if target_language == "Japanese":
            lang_script_rule = "Use ONLY Japanese Kanji/Kana for Japanese words. NEVER use Chinese Hanzi (e.g. 听 is WRONG, use 聞く). No Romaji."
        elif target_language == "Chinese":
            lang_script_rule = "Use ONLY Simplified Chinese characters for Chinese words. No Pinyin."
        elif target_language == "Korean":
            lang_script_rule = "Use ONLY Hangul for Korean words. No romanization."
        else:
            lang_script_rule = f"Use only native {target_language} script for {target_language} words."

        sp = f"""You are a strict {target_language} grammar checker.
IMPORTANT: Casual/informal speech is NOT a grammar error. Greetings, exclamations, and sentence fragments that are natural in conversation are CORRECT. Only flag real structural grammar errors (wrong particles, incorrect conjugation, impossible word order).

You MUST respond in this exact format:
Grammar Correct: [YES or NO]
Correction: [The corrected sentence, if NO. If YES, leave blank]
Explanation: [Write your explanation ENTIRELY IN ENGLISH. {lang_script_rule} All other words MUST be English. No Romaji. No Pinyin.]"""
        user_msg = f"Analyze the following sentence from a language learner: \"{user_text}\""
        try:
            raw = await self._complete(
                messages=[
                    {"role": "system", "content": sp},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.1,
                max_tokens=200
            )
            raw = raw.strip()
            
            if "Grammar Correct: [YES]" in raw or "Grammar Correct: YES" in raw:
                raw = "PERFECT"
            else:
                correction = ""
                explanation = ""
                for line in raw.split("\n"):
                    if line.startswith("Correction:"):
                        correction = line.replace("Correction:", "").strip().strip("[]")
                    elif line.startswith("Explanation:"):
                        explanation = line.replace("Explanation:", "").strip().strip("[]")
                
                if correction and explanation:
                    raw = f"Correction: {correction}\n\nExplanation: {explanation}"
                elif correction:
                    raw = f"Correction: {correction}"
                elif explanation:
                    raw = f"Explanation: {explanation}"

            self.word_bank_cache[cache_key] = raw
            return raw, True
        except Exception as e:
            return None, False

    # ---------- Grammar Tutor Chat ----------

    async def chat_with_grammar_tutor(self, user_question, original_text, grammar_correction, history, target_language):
        lang_script_rule = ""
        if target_language == "Japanese":
            lang_script_rule = "Use ONLY Japanese Kanji/Kana for Japanese words. NEVER use Chinese Hanzi (e.g. 听 is WRONG, use 聞く). No Romaji."
        elif target_language == "Chinese":
            lang_script_rule = "Use ONLY Simplified Chinese characters for Chinese words. No Pinyin."
        elif target_language == "Korean":
            lang_script_rule = "Use ONLY Hangul for Korean words. No romanization."
        else:
            lang_script_rule = f"Use only native {target_language} script for {target_language} words."

        sp = f"""Grammar tutor for {target_language}. Student said: "{original_text}". Correction: "{grammar_correction}"
Answer questions about this correction. Brief, encouraging, easy to understand.

RULES:
1. Explain ENTIRELY in English. The ONLY non-English text allowed is {target_language} words written in their native script.
2. {lang_script_rule}
3. No Romaji. No Pinyin. No romanization of any kind. BAD: "やあ (ya-ah)" GOOD: "やあ"
4. Be concise. Say each point once.
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
