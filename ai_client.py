# ai_client.py
import openai
from openai import OpenAI
import re
import config

class AIClient:
    def __init__(self, model_override=None):
        import os
        vllm_url = os.environ.get("VLLM_URL", "http://localhost:8000/v1")
        # We don't need a real API key for local vLLM, but the client requires the parameter
        api_key = os.environ.get("OPENAI_API_KEY", "dummy_key_for_vllm")
        
        self.client = OpenAI(
            base_url=vllm_url,
            api_key=api_key
        )
        self.model = model_override or "Qwen/Qwen2.5-7B-Instruct"
        self.conversation_history = [] 

    def clear_history(self):
        self.conversation_history = []
        
    def get_reply(self, user_text, target_language, difficulty="Intermediate"):
        system_prompt = f"""[ROLE]
You are a human language exchange partner chatting via text message. You are NOT an AI assistant. You are brief, natural, and highly conversational.

[CORE RULES - ALL LANGUAGES]
1. LENGTH LIMIT: Maximum 30 words. 1-2 sentences.
2. NO ESSAYS: Never use lists, bullet points, or multiple pieces of advice. ONE brief thought, ONE question.
3. THE TWO-WAY MIRROR (DYNAMIC FORMALITY):
   - You MUST match the user's exact level of formality based on their latest message.
   - If the user speaks formally, YOU MUST SPEAK FORMALLY.
   - If the user speaks casually/informally, YOU MUST SPEAK CASUALLY.
   - Do not mix formal and casual grammar in the same response.
4. SAFETY FILTER: Do not discuss or generate content that is violent, explicit, R-18, or inappropriate for a school environment. Graciously decline if prompted.

[LANGUAGE RULES: {target_language}]
1. EXCLUSIVE LANGUAGE: Speak ONLY in {target_language}.
"""

        if target_language == "Japanese":
            system_prompt += """2. JAPANESE FORMALITY DETECTION:
   - FORMAL MODE TRIGGER: If the user uses です, ます, でしょうか, or polite phrasing, you MUST reply using standard polite Japanese (丁寧語 - です/ます).
   - CASUAL MODE TRIGGER: If the user uses だ, 俺, さ, よ, or dictionary-form verbs, you MUST reply using casual Japanese (タメ口 - だ/ね/よ). In this mode, ZERO polite tokens (です/ます) are allowed.
3. IMMERSION: 100% Japanese vocabulary. Do not mix languages to accommodate beginners. NEVER output Romaji or pronunciation guides in parentheses. Output pure Japanese text only.

[CORRECT EXAMPLES OF MIRRORING]
User (Formal): 相談があるんですが、いいでしょうか？
You (Formal): もちろんです！どのようなご相談ですか？

User (Casual): 相談があるんだけど、いいかな？
You (Casual): もちろん！何でも聞いてね。"""
        else:
            system_prompt += f"""2. FORMALITY DETECTION: Strictly obey the 'Two-Way Mirror' rule for {target_language} grammar.\n3. IMMERSION: 100% {target_language} vocabulary. Do not mix languages to accommodate beginners."""

        # Inject difficulty rules
        diff_rules = config.DIFFICULTY_PROMPT_MODIFIERS.get(difficulty, config.DIFFICULTY_PROMPT_MODIFIERS["Intermediate"])
        system_prompt += f"""\n\n[DIFFICULTY LEVEL: {difficulty}]
You must strictly constrain your language to match the requested difficulty tier:
{diff_rules}"""

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": user_text})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2, 
                max_tokens=60
            )
            ai_reply = self._cleanup_text(response.choices[0].message.content)
            self.conversation_history.append({"role": "user", "content": user_text})
            self.conversation_history.append({"role": "assistant", "content": ai_reply})
            if len(self.conversation_history) > 12: self.conversation_history = self.conversation_history[-12:]
            return ai_reply, True
        except Exception as e:
            return f"Error: {str(e)}", False
        
    def get_stateless_reply(self, prompt):
        """Used for the Grammar Tutor. Does not read from or save to conversation history."""
        
        system_prompt = """[ROLE]
You are an expert language grammar tutor. 
Your job is to explain grammar, sentence structure, and vocabulary clearly and concisely in English. 
Break down the components of the sentences provided to you so a learner can easily understand them.
Feel free to use formatting like bullet points or newlines if it helps clarify the grammar."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2, 
                max_tokens=300 # Explanations need more tokens than the 60 used in standard chat
            )
            # We don't use self._cleanup_text here because we WANT to allow 
            # newlines and bullet points for grammar explanations.
            ai_reply = response.choices[0].message.content.strip()
            return ai_reply, True
            
        except Exception as e:
            return f"Error: {str(e)}", False

    def _cleanup_text(self, text):
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines if any(c.isalnum() for c in line)]
        reply = " ".join(cleaned_lines)
        reply = re.sub(r'^[。・•\-\*]\s*', '', reply)
        return reply.strip()

    def get_scenario_intro(self, target_language, scenario_dict):
        system_prompt = f"""[ROLE]
You are a participant in a roleplay scenario. 
SCENARIO: {scenario_dict['title']}
YOUR ROLE: {scenario_dict['ai_role']}
PERSONA INSTRUCTIONS: {scenario_dict.get('persona_instruction', '')}
USER'S ROLE: {scenario_dict['user_role']}
USER'S GOAL: {scenario_dict['goal']}

[RULES]
1. Stay in character at all times. Do not break character.
2. IMMERSION: Speak 100% in {target_language}.
3. STRICT CHARACTER FILTER: For Japanese, your response must ONLY use native characters (Hiragana, Katakana, Kanji). Do NOT use Romaji or English letters.
4. Respond briefly and naturally. Maximum 30 words.
"""
        user_prompt = f"We are starting the roleplay scenario. Your instruction is: '{scenario_dict['start_instruction']}'. Write exactly ONE brief opening line in {target_language} to start the conversation naturally."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2, 
                max_tokens=60
            )
            ai_reply = self._cleanup_text(response.choices[0].message.content)
            return ai_reply, True
        except Exception as e:
            return f"Error: {str(e)}", False

    def get_scenario_reply(self, user_text, target_language, scenario_dict):
        self.conversation_history.append({"role": "user", "content": user_text})
        
        system_prompt = f"""[ROLE]
You are a participant in a roleplay scenario. 
SCENARIO: {scenario_dict['title']}
YOUR ROLE: {scenario_dict['ai_role']}
PERSONA INSTRUCTIONS: {scenario_dict.get('persona_instruction', '')}
USER'S ROLE: {scenario_dict['user_role']}
USER'S GOAL: {scenario_dict['goal']}

[RULES]
1. Stay in character at all times. Do not break character.
2. IMMERSION: Speak 100% in {target_language}.
3. STRICT CHARACTER FILTER: For Japanese, your response must ONLY use native characters (Hiragana, Katakana, Kanji). Do NOT use Romaji or English letters (the only exception is the goal tag mentioned in Rule 6).
4. Respond briefly and naturally. Maximum 30 words.
5. GOAL EVALUATION: Read the USER's GOAL carefully. You must evaluate if the user's latest message conclusively achieves this goal.
6. If and ONLY if the user has completely achieved their goal, you MUST append the exact string "[GOAL_REACHED]" to the end of your response. Under NO circumstances should you output this string if the user is merely asking a question or hasn't finalized their action.
"""

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.conversation_history)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2, 
                max_tokens=60
            )
            ai_reply = self._cleanup_text(response.choices[0].message.content)
            
            # Save the raw reply to history so the AI sees [GOAL_REACHED] in its own memory
            self.conversation_history.append({"role": "assistant", "content": ai_reply})
            return ai_reply, True
        except Exception as e:
            # Revert the user's message from history on failure
            self.conversation_history.pop()
            return f"Error: {str(e)}", False

    def get_scenario_critique(self, target_language):
        system_prompt = f"""You are an expert language teacher evaluating a student's roleplay performance in {target_language}.
Below is a transcript of the scenario. The student was the user.
Please provide a brief, constructive critique in English. 
Point out what they did well, any unnatural phrasing or grammar mistakes they made, and how they could improve.

CRITICAL RULES:
1. ONLY critique the Student's lines. Do NOT critique the AI Partner's lines.
2. Be lenient with conversational phrasing. Phrases like "〜とかありますか" or "じゃあ〜でお願いします" are perfectly natural in casual/polite blending. Do not penalize them.
3. Only point out actual severe grammatical errors or inappropriate vocabulary.

Keep your critique concise and actionable. Do not use Markdown headings, just plain text with simple bullet points if needed.
"""
        # Convert history into a readable transcript
        transcript = []
        for msg in self.conversation_history:
            role = "Student" if msg["role"] == "user" else "AI Partner"
            transcript.append(f"{role}: {msg['content']}")
            
        transcript_str = "\n".join(transcript)
        user_prompt = f"[TRANSCRIPT]\n{transcript_str}\n\n[CRITIQUE REQUIRED]"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2, 
                max_tokens=250
            )
            return response.choices[0].message.content.strip(), True
        except Exception as e:
            return f"Critique Generation Error: {str(e)}", False

    def get_pronunciation_feedback(self, lang, analysis_data):
        system_prompt = f"""You are an expert {lang} pronunciation coach.
The user just spoke the phrase: "{analysis_data['text']}"

Here is the acoustic analysis of their speech compared to a native speaker reference:
- Overall Naturalness Score: {analysis_data['overall_score']}/100
- Pitch/Intonation Match: {analysis_data['pitch_score']}/100
- Stress/Intensity Match: {analysis_data['stress_score']}/100
- Rhythm Match: {analysis_data['rhythm_score']}/100
- User Duration: {analysis_data['user_duration']}s (Reference: {analysis_data['ref_duration']}s)

Provide short, encouraging, actionable feedback.
1. Start with an overall assessment (e.g. "Natural", "Slightly Off", "Hard to Understand").
2. Highlight one thing they did well.
3. Suggest one specific area for improvement based on the lowest score (e.g., if rhythm is low, mention pacing; if pitch is low, mention intonation or tone).
Keep it under 3 sentences."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}],
                temperature=0.7,
                max_tokens=150
            )
            return response.choices[0].message.content.strip(), True
        except Exception as e:
            return f"Failed to generate feedback: {str(e)}", False