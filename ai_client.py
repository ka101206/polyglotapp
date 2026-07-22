# ai_client.py
import os
import re
import asyncio
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
        self.kana_cache = {}  # Japanese text -> hiragana reading (for TTS)

        # Durable, capped profile of the user (name, pets, job, preferences).
        # Overwritten on refresh so it can never grow unbounded; injected cheaply
        # into every reply so even LOW/balanced mode remembers key facts.
        self.profile_memory = ""
        self._bg_tasks = []
        self._turn_count = 0

    # ---------- Shared helpers ----------

    # By splitting on commas as well as periods, we send smaller chunks to the TTS engine.
    # This drastically reduces the "time to first audio" latency, making the app feel much faster!
    SENTENCE_TERMINATORS = ['。', '！', '？', '.', '!', '?', '、', ',']

    # Compact difficulty hints for LOW mode (cheap; full modifiers live in config).
    LOW_DIFFICULTY_HINTS = {
        "Beginner": "very simple, basic vocabulary; short, easy sentences.",
        "Elementary": "common everyday words; simple sentences.",
        "Intermediate": "varied everyday vocabulary; moderately complex sentences.",
        "Pre-Advanced": "broad vocabulary with some idioms; complex sentences.",
        "Advanced": "natural native-level vocabulary, idioms, and full grammatical range.",
    }

    def clear_history(self):
        self.conversation_history = []
        self.scenario_history = []

    # Regex matching each target language's native script. Used to detect where
    # the actual reply begins (vs. any leftover reasoning preamble).
    _NATIVE_SCRIPT_PATTERNS = {
        "Japanese": r'[぀-ゟ゠-ヿ一-龯]',
        "Chinese":  r'[一-龯]',
        "Korean":   r'[가-힣ᄀ-ᇿ]',
        "Spanish":  r'[A-Za-zÀ-ſ]',
        "French":   r'[A-Za-zÀ-ſ]',
        "Italian":  r'[A-Za-zÀ-ſ]',
        "English":  r'[A-Za-z]',
    }
    _LATIN_LANGUAGES = ("Spanish", "French", "Italian", "English")

    def _cleanup_text(self, text, language="Japanese"):
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        text = re.sub(r'(?is)Here\'s a thinking process.*?</think>', '', text)
        text = re.sub(r'(?is)Here\'s a thinking process.*?✅\s*', '', text)
        text = re.sub(r'\[GOAL_REACHED\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(?is)Here\'s a thinking process.*?(?=(?:こんにちは|承知|分かり|はい|いいえ|もちろん|そうですね|よろしく|初めまして|[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]))', '', text)
        native = self._NATIVE_SCRIPT_PATTERNS.get(language, self._NATIVE_SCRIPT_PATTERNS["Japanese"])
        latin_script = language in self._LATIN_LANGUAGES

        # Reasoning/meta lines to strip from the preamble. For Latin-script target
        # languages the reply's native script IS Latin (same as any reasoning),
        # so we must NOT strip on a leading digit \u2014 a real reply can start with a
        # number (e.g. "10 dollars, please."). We only strip explicit meta phrases
        # and bullet markers there. CJK targets keep the stricter digit stripping.
        if latin_script:
            reasoning_re = r"(?i)^(?:[\-\*\u2022]\s|(?:Here'?s|Here is|Okay|Alright|Sure, here|Analyze|Identify|Determine|Draft|Final Check|Checking|Let me|First,|Step \d)\b)"
        else:
            reasoning_re = r"^[\d\.\-\*]|Here's|Analyze|Identify|Determine|Draft|Final Check|Checking"

        lines = text.split('\n')
        cleaned = []
        in_reasoning = True
        for l in lines:
            stripped = l.strip()
            if not stripped:
                continue

            # Drop meta/reasoning preamble lines. For CJK targets, a line that
            # already contains native script is treated as the real reply even if
            # it matches the pattern (e.g. "1. \u79C1\u306F\u2026"); for Latin targets we can't
            # use native script to disambiguate, so rely on the pattern alone.
            if in_reasoning and re.match(reasoning_re, stripped) and (latin_script or not re.search(native, stripped)):
                continue

            in_reasoning = False
            cleaned.append(stripped)

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
        msg = response.choices[0].message
        # With thinking disabled, some vLLM reasoning parsers still route the
        # reply into reasoning/reasoning_content instead of content.
        text = (msg.content
                or getattr(msg, "reasoning", None)
                or getattr(msg, "reasoning_content", None)
                or "")
        return text.strip()

    async def _stream_sentences(self, messages, temperature=0.2, max_tokens=150, language="Japanese"):
        """Async generator that yields (text_delta, sentence_text, full_reply, success, is_done, extras)."""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                stream_options={"include_usage": True},
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )

            full_text = ""
            yielded_len = 0
            sentence_buf = ""
            safe_reply = ""
            extras = {"goal_reached": False}

            async for chunk in stream:
                if hasattr(chunk, 'usage') and chunk.usage:
                    extras["tokens"] = chunk.usage.total_tokens

                _delta = chunk.choices[0].delta if chunk.choices else None
                token = None
                if _delta is not None:
                    # Thinking is disabled, but some vLLM reasoning parsers route
                    # the reply into reasoning/reasoning_content instead of content.
                    token = (_delta.content
                             or getattr(_delta, "reasoning", None)
                             or getattr(_delta, "reasoning_content", None))
                if token:
                    full_text += token

                    reply_part = full_text
                    safe_reply = self._cleanup_text(reply_part, language)
                    
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

    async def get_reply_stream(self, user_text, target_language, difficulty="Intermediate", enable_grammar=True, enable_word_bank=True, user_name=None, notebook_words=None, voice_gender="female", token_mode="high"):
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

        lang_rules = {
            "Japanese": {"script": "Japanese ONLY. No Romaji/English.", "CASUAL": "タメ口. Use だ/だよ.", "FORMAL": "丁寧語 (です/ます)."},
            "Korean": {"script": "Hangul ONLY. No English/romanization.", "CASUAL": "반말. No 요/세요.", "FORMAL": "해요체 (요)."},
            "Chinese": {"script": "Simplified Chinese ONLY. No Pinyin/English.", "CASUAL": "Use 你.", "FORMAL": "Use 您."},
        }

        lang = lang_rules.get(target_language, {
            "script": f"{target_language} ONLY.",
            "CASUAL": "casual",
            "FORMAL": "formal",
        })

        # Relationship follows the user's tone: a casual friend, or a warmer, more
        # respectful native speaker when they're being formal.
        relationship = ("a close friend texting casually" if register == "CASUAL"
                        else "a warm, polite native speaker chatting respectfully")

        system_prompt = f"""Role: You are {relationship} — a real, opinionated native {target_language} speaker.

Rules:
- 1-2 short sentences, <30 words. Natural, idiomatic phrasing (e.g. "steak", not "meat steak").
- React, agree, joke, or ask. Match user's energy.
- No heavy/sensitive topics.
- Register: {register} ({lang[register]})
- Script: {lang['script']}"""

        if token_mode == "low":
            system_prompt = (
                f"Role: You are {relationship} — a real, opinionated native {target_language} speaker.\n"
                f"- 1-2 short sentences, <30 words. Natural, idiomatic phrasing (e.g. \"steak\", not \"meat steak\").\n"
                f"- React, agree, joke, or ask. Match the user's energy.\n"
                f"- Register: {register} ({lang[register]}). Script: {lang['script']}."
            )
        
        if target_language == "English":
            system_prompt += "\nCRITICAL: You MUST answer strictly in natural, idiomatic English. ONLY output English text."
        else:
            system_prompt += f"\nCRITICAL: You MUST answer strictly in {target_language}. Do NOT use English conversational fillers (like 'WELL', 'OH', etc.). ONLY output {target_language} text."

        gender_rules = f"You are a {voice_gender}. Match your speaking style, tone, and self-referential pronouns to your gender ({voice_gender})."
        if target_language == "Japanese":
            if voice_gender == "male":
                gender_rules += " When referring to yourself, use '俺', '僕', or '私' (for formal)."
            else:
                gender_rules += " When referring to yourself, use '私', 'うち', 'あたし', or '僕' (for 僕っこ)."
        
        system_prompt += f"\n- Persona: {gender_rules}"
        system_prompt += "\n- Plain text only: never use emojis, emoticons, or kaomoji."
        system_prompt += "\n- You are a real person with genuine opinions, tastes, and experiences. ALWAYS give a real answer or preference and keep the conversation going (add a natural follow-up). NEVER say you are an AI, that you have no preferences, or that you cannot answer."

        # Difficulty calibration applies to BOTH modes — a beginner must never get
        # advanced replies, even in low-token mode.
        _bd = "Intermediate"
        if "Beginner" in difficulty: _bd = "Beginner"
        elif "Elementary" in difficulty: _bd = "Elementary"
        elif "Pre-Advanced" in difficulty or "Upper Intermediate" in difficulty: _bd = "Pre-Advanced"
        elif "Intermediate" in difficulty: _bd = "Intermediate"
        elif "Advanced" in difficulty: _bd = "Advanced"
        if token_mode == "low":
            system_prompt += f"\n- Level ({difficulty}): {self.LOW_DIFFICULTY_HINTS[_bd]}"

        if token_mode == "high":
            diff_rules = config.DIFFICULTY_PROMPT_MODIFIERS.get(_bd, config.DIFFICULTY_PROMPT_MODIFIERS["Intermediate"])
            system_prompt += f"\nDifficulty: {difficulty}. {diff_rules}"

            if user_name:
                system_prompt += f"\n[USER INFO] The user's name is \"{user_name}\". Write it verbatim (same characters/script); never romanize, transliterate, or re-spell it, and don't ask for their name."

            if self.conversation_memory:
                system_prompt += f"\n\n[Previous context]\n{self.conversation_memory}"

            # Anti-circular: when conversation is long enough, nudge towards notebook topics
            if len(self.conversation_history) >= 6:
                system_prompt += "\n\nCRITICAL INSTRUCTION: Analyze the recent conversation. If the user is just giving short 1-word answers (like 'OK', 'うん') or the conversation is stuck in a repetitive loop (e.g. endlessly agreeing or 'getting ready'), you MUST forcefully change the subject to something entirely new right now. Ask a completely unrelated question to force the conversation forward."
                if notebook_words:
                    topics_str = ", ".join(notebook_words[:15])
                    system_prompt += f" For example, the user is interested in these topics: [{topics_str}]. Try asking about one of them!"

        # Capped, durable user profile — cheap to inject, so even LOW mode remembers.
        if self.profile_memory:
            system_prompt += f"\n[Remember about the user] {self.profile_memory}"

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
        async for delta, sentence, full_reply, ok, done, extras in self._stream_sentences(messages, temperature=0.5, language=target_language):
            full = full_reply

            if done and ok:
                self.conversation_history.append({"role": "user", "content": user_text})
                self.conversation_history.append({"role": "assistant", "content": self._cleanup_text(full, target_language)})
                
                # Refresh the capped user profile every 3 turns (background, amortized).
                # Snapshot user messages now, before any history truncation below.
                # Turn counter (not history length) so cadence is stable regardless
                # of the sliding-window truncation below.
                self._turn_count += 1
                if self._turn_count % 3 == 0:
                    snap = [m["content"] for m in self.conversation_history if m.get("role") == "user"][-8:]
                    self._bg_tasks = [t for t in self._bg_tasks if not t.done()]
                    self._bg_tasks.append(asyncio.create_task(self.update_profile_memory(snap)))

                if token_mode == "low":
                    if len(self.conversation_history) > 10:
                        self.conversation_history = self.conversation_history[-10:]
                else:
                    # Compaction Layer (after 16 messages / 8 turns)
                    if len(self.conversation_history) > 16:
                        to_compact = self.conversation_history[:-8]
                        self.conversation_history = self.conversation_history[-8:]
                        asyncio.create_task(self._compact_history(to_compact))
                    
            yield delta, sentence, full_reply, ok, done, extras
            if not ok or done:
                break

    async def _compact_history(self, msgs_to_compact):
        try:
            text = "\n".join([f"{m['role']}: {m['content']}" for m in msgs_to_compact])
            prompt = f"Summarize this chat history concisely:\n{text}"
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=150,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            _m = resp.choices[0].message
            summary = ((_m.content
                        or getattr(_m, "reasoning", None)
                        or getattr(_m, "reasoning_content", None)
                        or "")).strip()
            if self.conversation_memory:
                # Cap so the topic summary can't grow unbounded over long sessions.
                self.conversation_memory = (self.conversation_memory + " " + summary)[-800:]
            else:
                self.conversation_memory = summary
        except Exception as e:
            print(f"[Compaction Error] {e}", flush=True)

    # Hard cap on the injected profile (~70 tokens) so per-turn cost stays bounded.
    MAX_PROFILE_CHARS = 280

    async def update_profile_memory(self, user_msgs):
        """Re-summarize durable facts about the user (name, family, pets, job, home,
        hobbies, strong likes/dislikes) into one compact, capped line. OVERWRITES the
        previous note (never appends), so it cannot grow without bound. Background,
        best-effort — failures are swallowed so chat is never affected."""
        try:
            convo = "\n".join(m for m in user_msgs if m)
            if not convo.strip():
                return
            sys = ("Extract DURABLE facts about the user (name, family, pets, job, home, "
                   "hobbies, strong likes/dislikes) from their messages. Merge with the "
                   "current notes, dedupe, and output ONE compact line of at most 6 facts, "
                   "semicolon-separated, e.g. 'name: Ken; dog: Max; likes: action movies'. "
                   "Under 40 words. Omit anything transient. If nothing durable, output NONE.")
            usr = f"Current notes: {self.profile_memory or '(none)'}\nUser messages:\n{convo}"
            out = await self._complete(
                [{"role": "system", "content": sys}, {"role": "user", "content": usr}],
                temperature=0.0, max_tokens=80,
            )
            out = (out or "").strip()
            if out and out.upper() != "NONE":
                self.profile_memory = out[:self.MAX_PROFILE_CHARS]
        except Exception as e:
            print(f"[Profile Memory Error] {e}", flush=True)

    # ---------- Scenarios ----------

    def start_scenario(self, intro_text):
        self.scenario_history = [{"role": "assistant", "content": intro_text}]

    async def get_scenario_reply_stream(self, user_text, target_language, difficulty, scenario_dict, enable_grammar=True, enable_word_bank=True, user_name=None, voice_gender="female", token_mode="high"):
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
3. ABSOLUTE LANGUAGE RULE: {"Speak 100% ONLY in natural, idiomatic English." if target_language == "English" else f"Speak 100% ONLY in {target_language}. NO Romaji. NO Pinyin. NO English (except acronyms like OK). Write ONLY in the native script of {target_language}. For Japanese: no Chinese Hanzi—use only Japanese Kanji."}
4. Max 30 words. {handholding} Speak like a true native. Use natural, native, and idiomatic phrasing. Avoid redundant, weird, or overly explicit translated phrases (e.g. say "steak", not "meat steak").
5. VERY IMPORTANT: The moment the user achieves the goal ({scenario_dict['goal']}), you MUST append the exact string "[GOAL_REACHED]" to the END of your reply. Do not forget!
6. Do NOT ask the user for their name."""

        if token_mode == "low":
            system_prompt = (
                f"Scenario: {scenario_dict['title']}. You are the {scenario_dict['ai_role']}. Goal: {scenario_dict['goal']}\n"
                f"1. Speak 100% in {target_language} ONLY. Max 30 words. Stay in character. Sound like a true native — natural, idiomatic phrasing; match the user's tone.\n"
                f"2. VERY IMPORTANT: The moment the user achieves the goal ({scenario_dict['goal']}), you MUST append the exact string \"[GOAL_REACHED]\" to the END of your reply. Do not forget!"
            )
            _bd = "Intermediate"
            if "Beginner" in difficulty: _bd = "Beginner"
            elif "Elementary" in difficulty: _bd = "Elementary"
            elif "Pre-Advanced" in difficulty or "Upper Intermediate" in difficulty: _bd = "Pre-Advanced"
            elif "Intermediate" in difficulty: _bd = "Intermediate"
            elif "Advanced" in difficulty: _bd = "Advanced"
            system_prompt += f"\n3. Level ({difficulty}): {self.LOW_DIFFICULTY_HINTS[_bd]}"

        gender_rules = f"You are a {voice_gender}. Match your speaking style, tone, and self-referential pronouns to your gender ({voice_gender})."
        if target_language == "Japanese":
            if voice_gender == "male":
                gender_rules += " When referring to yourself, use '俺', '僕', or '私' (for formal)."
            else:
                gender_rules += " When referring to yourself, use '私', 'うち', 'あたし', or '僕' (for 僕っこ)."

        system_prompt += f"\n7. Persona: {gender_rules}"
        system_prompt += "\n8. Plain text only: never use emojis, emoticons, or kaomoji."
        system_prompt += "\n9. Stay fully in character: never mention being an AI or say you cannot answer — keep the interaction going in-role."

        if token_mode == "high" and user_name:
            system_prompt += f"\n[USER INFO] The user's name is \"{user_name}\". Write it verbatim (same characters/script); never romanize, transliterate, or re-spell it, and don't ask for their name."

        system_prompt += """

CRITICAL OUTPUT FORMATTING:
Output ONLY your conversational reply (and the [GOAL_REACHED] tag if the goal is met). DO NOT output any thinking process, analysis, meta-commentary, or prefixes like 'Here is a thinking process'. Just output the raw conversational reply text directly."""

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.scenario_history)

        full = ""
        async for delta, sentence, full_reply, ok, done, extras in self._stream_sentences(messages, language=target_language):
            full = full_reply
            
            if done and ok:
                self.scenario_history.append({"role": "assistant", "content": self._cleanup_text(full, target_language)})
                if token_mode == "low":
                    if len(self.scenario_history) > 10:
                        self.scenario_history = self.scenario_history[-10:]
                else:
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
   - Style preferences (e.g. using kanji vs hiragana for words like 事 vs こと, or omitted particles that are common in casual speech)
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

    # ---------- Japanese reading for TTS ----------

    @staticmethod
    def _katakana_to_hiragana(s):
        return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)

    def _local_kana(self, text):
        """Dictionary-grade hiragana reading via OpenJTalk (+ user dict). No LLM call.
        Common words read correctly; rare kanji/proper nouns rely on jp_userdict.csv
        (the same corrections the TTS uses). Returns hiragana or None."""
        try:
            import pyopenjtalk
            try:
                from jp_userdict import ensure_user_dict_loaded
                ensure_user_dict_loaded()
            except Exception:
                pass
            kata = (pyopenjtalk.g2p(text, kana=True) or "").replace(" ", "")
            return self._katakana_to_hiragana(kata) if kata else None
        except Exception:
            return None

    async def to_kana(self, text):
        """Hiragana reading for TTS. Dictionary-first (OpenJTalk, zero tokens); falls
        back to the context-aware LLM only if the local reading looks unreliable."""
        text = (text or "").strip()
        if not text:
            return None
        if text in self.kana_cache:
            return self.kana_cache[text]
        # Dictionary-first: local OpenJTalk reading, no LLM tokens.
        local = self._local_kana(text)
        if local and re.search(r"[぀-ゟ]", local) and not re.search(r"[一-龯]", local):
            self.kana_cache[text] = local
            return local
        try:
            out = await self._complete(
                [
                    {"role": "system", "content": "Convert the Japanese text to its hiragana reading. Output ONLY hiragana and the original punctuation — no kanji, no katakana loanword spelling changes, no romaji, no explanation. Keep it a faithful reading of the input."},
                    {"role": "user", "content": text},
                ],
                temperature=0.0, max_tokens=120,
            )
            out = (out or "").strip()
            # Sanity: must contain kana and must not still contain kanji, else the
            # conversion failed — fall back to the original text.
            if out and re.search(r"[぀-ゟ゠-ヿ]", out) and not re.search(r"[一-龯]", out):
                self.kana_cache[text] = out
                return out
        except Exception:
            pass
        return None

    # ---------- Definitions ----------

    # Per-language instruction for the notebook "Reading" line.
    READING_INSTRUCTIONS = {
        # Japanese: kana furigana only — never romaji.
        "Japanese": "the reading in hiragana furigana ONLY. Do NOT use romaji or any Latin letters.",
        # Chinese: pinyin with tone marks.
        "Chinese": "the reading in pinyin, with tone marks.",
        # Korean: Latin-alphabet romanization (Revised Romanization).
        "Korean": "the reading romanized in the Latin alphabet (Revised Romanization of Korean).",
        # Latin-script languages: IPA pronunciation.
        "English": "the pronunciation in IPA (International Phonetic Alphabet), e.g. /bəˈnɑːnə/",
        "Spanish": "the pronunciation in IPA (International Phonetic Alphabet)",
        "French": "the pronunciation in IPA (International Phonetic Alphabet)",
        "Italian": "the pronunciation in IPA (International Phonetic Alphabet)",
    }

    # Per-language extra annotation line for the notebook: (Label, instruction).
    # Parsed and rendered above the reading on the frontend. Keep the Label a
    # single English word — the frontend maps it to a localized display label.
    ANNOTATION_INSTRUCTIONS = {
        # Japanese: standard Tokyo-dialect pitch accent.
        "Japanese": ("Pitch", "the standard Tokyo-dialect pitch-accent pattern as the accent type and drop position, e.g. '平板 [0]', '頭高 [1]', '中高 [2]', '尾高 [3]'"),
        # Chinese: tone number of each syllable.
        "Chinese": ("Tone", "the tone number of each syllable separated by hyphens (1-4, or 0/5 for neutral), e.g. '3-3', '4-1', '2-0'"),
        # English: which syllable carries primary stress.
        "English": ("Stress", "the word split into syllables with the STRESSED syllable in CAPITAL letters, e.g. 'ba-NA-na', 'COM-pu-ter'"),
        # Romance languages: grammatical gender of nouns.
        "Spanish": ("Gender", "if the word is a noun, its grammatical gender with definite article (el = masculine, la = feminine), e.g. 'la (feminine)'; otherwise write N/A"),
        "French": ("Gender", "if the word is a noun, its grammatical gender with definite article (le = masculine, la = feminine), e.g. 'le (masculine)'; otherwise write N/A"),
        "Italian": ("Gender", "if the word is a noun, its grammatical gender with definite article (il/lo = masculine, la = feminine), e.g. 'la (feminine)'; otherwise write N/A"),
    }

    async def get_definition(self, word, context, target_language):
        reading_instruction = self.READING_INSTRUCTIONS.get(
            target_language, "the pronunciation. If not applicable, write N/A"
        )
        annotation = self.ANNOTATION_INSTRUCTIONS.get(target_language)
        fmt_lines = [f"Reading: <{reading_instruction}>"]
        # Japanese pitch accent is computed locally from OpenJTalk (dictionary-grade),
        # so we don't ask the LLM for it — it's injected after the response instead.
        if annotation and target_language != "Japanese":
            fmt_lines.append(f"{annotation[0]}: <{annotation[1]}>")
        fmt_lines.append("<A short, concise definition in English>")
        fmt = "\n".join(fmt_lines)
        system_prompt = f"""You are a {target_language} dictionary.
Given the word '{word}' and the context '{context}', provide its meaning in English.
Format your response exactly like this:
{fmt}"""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Define '{word}' in the context of: {context}"}
            ]
            response = await self._complete(messages, temperature=0.1, max_tokens=160)
            if not response:
                return "Definition not available."
            response = response.strip()
            if target_language == "Japanese":
                response = self._inject_japanese_pitch(word, response)
            return response
        except Exception:
            return "Definition not available."

    @staticmethod
    def _inject_japanese_pitch(word, text):
        """Replace/insert the notebook 'Pitch:' line with the OpenJTalk-computed
        pitch accent, placed right after the 'Reading:' line."""
        try:
            from jp_pitch import get_pitch_accent
            pitch = get_pitch_accent(word)
        except Exception:
            pitch = None
        if not pitch:
            return text
        # Drop any model-provided Pitch line, then insert our own after Reading.
        lines = [l for l in text.split("\n") if not re.match(r"^\s*Pitch\s*:", l, re.I)]
        out, inserted = [], False
        for l in lines:
            out.append(l)
            if not inserted and re.match(r"^\s*Reading\s*:", l, re.I):
                out.append(f"Pitch: {pitch}")
                inserted = True
        if not inserted:
            out.insert(0, f"Pitch: {pitch}")
        return "\n".join(out)
    # ---------- Word Bank ----------

    async def generate_word_bank(self, reply_text, target_language, include_decoys=False, token_mode="high"):
        cache_key = f"{target_language}:{reply_text.strip().lower()}:{include_decoys}"
        if cache_key in self.word_bank_cache:
            return self.word_bank_cache[cache_key], True

        count = 15 if include_decoys else 10
        script_rule = "" if target_language == "English" else " (NO CHINESE HANZI, NO ENGLISH)"
        sp = f"""You are a helpful language tutor.
Provide exactly {count} useful vocabulary words in {target_language}{script_rule} that the user could use to reply.
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

    async def analyze_grammar(self, user_text, target_language, difficulty, context_history=None, token_mode="high"):
        cache_key = f"grammar:{target_language}:{user_text.strip().lower()}:{hash(str(context_history))}"
        if cache_key in self.word_bank_cache:
            cached = self.word_bank_cache[cache_key]
            return cached[0], cached[1], True, (cached[2] if len(cached) > 2 else None)

        lang_script_rule = ""
        if target_language == "Japanese":
            lang_script_rule = "Use ONLY Japanese Kanji/Kana for Japanese words. NEVER use Chinese Hanzi (e.g. 听 is WRONG, use 聞く). ABSOLUTELY NO ROMAJI allowed anywhere."
        elif target_language == "Chinese":
            lang_script_rule = "Use ONLY Simplified Chinese characters for Chinese words. ABSOLUTELY NO PINYIN allowed anywhere."
        elif target_language == "Korean":
            lang_script_rule = "Use ONLY Hangul for Korean words. ABSOLUTELY NO ROMANIZATION allowed anywhere."
        else:
            lang_script_rule = f"Use only native {target_language} script for {target_language} words."

        sp = f"""Role: Strict {target_language} grammar checker for a CONVERSATION.
Rules:
- Casual speech, short responses, and sentence fragments are perfectly CORRECT in a conversation.
- If the sentence makes sense in the provided Context, DO NOT flag it as an error.
- Only flag severe structural errors (wrong conjugation, broken syntax).
- The Explanation MUST be written entirely in English.

Format:
Grammar Score: [0-100 integer. 100=perfect, 90+=minor style issue, 70-89=noticeable errors, below 70=major errors]
Grammar Correct: YES/NO
Correction: [if NO]
Explanation: [Entirely in English. {lang_script_rule}]
Category: [if NO: a short 2-4 word grammar error TYPE in English for tracking weak points, e.g. "particle usage", "verb conjugation", "word order", "wrong tense". if YES: NONE]"""
        user_msg = ""
        if context_history:
            user_msg += f"Context:\n{context_history}\n\n"
        user_msg += f"Sentence:\n\"{user_text}\""
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

            # Parse numeric grammar score
            grammar_score = 85  # default
            import re as _re
            score_match = _re.search(r'Grammar Score:\s*(\d+)', raw)
            if score_match:
                grammar_score = max(0, min(100, int(score_match.group(1))))
            
            weak_key = None
            if "Grammar Correct: [YES]" in raw or "Grammar Correct: YES" in raw:
                grammar_score = max(grammar_score, 95)  # Ensure high score for correct grammar
                feedback = "PERFECT"
            else:
                correction = ""
                explanation = ""
                category = ""
                for line in raw.split("\n"):
                    if line.startswith("Correction:"):
                        correction = line.replace("Correction:", "").strip().strip("[]")
                    elif line.startswith("Explanation:"):
                        explanation = line.replace("Explanation:", "").strip().strip("[]")
                    elif line.startswith("Category:"):
                        category = line.replace("Category:", "").strip().strip("[]")

                if category and category.upper() not in ("NONE", "N/A", ""):
                    weak_key = category.lower()

                if correction and explanation:
                    feedback = f"Correction: {correction}\n\nExplanation: {explanation}"
                elif correction:
                    feedback = f"Correction: {correction}"
                elif explanation:
                    feedback = f"Explanation: {explanation}"
                else:
                    feedback = raw

            self.word_bank_cache[cache_key] = (feedback, grammar_score, weak_key)
            return feedback, grammar_score, True, weak_key
        except Exception as e:
            return None, 0, False, None

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
1. You MUST explain ENTIRELY in English. Do NOT explain in Russian or Chinese or any other language.
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
CRITICAL: You MUST answer ENTIRELY in English. Do NOT answer in Russian, Chinese, or any other language except to quote the text being analyzed. 
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
