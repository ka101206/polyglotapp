import requests
import config

class DictionaryClient:
    def __init__(self):
        self.api_url = f"{config.AI_API_URL}/chat/completions"
        self.model = config.AI_MODEL
        self.api_key = config.API_KEY

    def fetch_definition(self, word, lang, immersion_mode=False):
        # 1. Setup Labels
        # Only uses target language labels if immersion_mode is True.
        if immersion_mode:
            labels = {
                "Japanese": ("単語", "意味", "例文"),
                "Spanish": ("Palabra", "Definición", "Ejemplo"),
                "French": ("Mot", "Définition", "Exemple"),
                "Chinese": ("单词", "定义", "例句"),
                "Korean": ("단어", "정의", "예문"),
                "Italian": ("Parola", "Definizione", "Esempio")
            }
            lbl_word, lbl_def, lbl_ex = labels.get(lang, ("Word", "Definition", "Example"))
        else:
            lbl_word, lbl_def, lbl_ex = "Word", "Definition", "Example"

        # 2. Get Definition 
        # If immersion is ON, we use a prompt that strictly forbids English.
        definition = self._get_definition(word, lang, immersion_mode)

        # 3. Get Example Sentence
        # Prevents "helpful" English translations from appearing in immersion mode.
        example = self._get_example(word, lang, immersion_mode)

        # 4. Final Construction
        return f"{lbl_word}: {word}\n{lbl_def}: {definition}\n{lbl_ex}: {example}", True

    def _get_definition(self, word, lang, immersion_mode):
        target_lang = lang if immersion_mode else "English"
        
        # This prompt only enforces "No English" if immersion_mode is active.
        prompt = f"Explain the meaning of the {lang} word '{word}' using ONLY {target_lang}."
        if immersion_mode:
            prompt += " Do not include any English translations or characters."

        return self._call_ai(prompt, target_lang, immersion_mode)

    def _get_example(self, word, lang, immersion_mode):
        # This prevents the specific bug where the AI adds an English line to the example.
        prompt = f"Write one natural {lang} example sentence using the word '{word}'."
        if immersion_mode:
            prompt += f" Output ONLY the {lang} sentence. Do NOT provide an English translation."
        else:
            prompt += " Output ONLY the sentence."

        return self._call_ai(prompt, lang, immersion_mode)

    def _call_ai(self, prompt, target_lang, immersion_mode):
        # System role is adjusted ONLY for immersion mode to block English.
        system_content = f"You are a native {target_lang} speaker."
        if immersion_mode:
            system_content += " You do not speak English and will never use English characters."

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "stream": False
        }
        
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                # Safety net: If the AI still adds a second line (translation), we cut it off.
                return content.split('\n')[0].strip('"')
            return "Error."
        except:
            return "Service unavailable."