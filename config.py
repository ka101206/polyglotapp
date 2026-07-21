# config.py
import os

# --- API Settings ---
API_KEY = "ollama" 

# --- Language Definitions ---
SUPPORTED_LANGUAGES = ["Japanese", "Spanish", "French", "Italian", "Chinese", "Korean", "English"]
JAPANESE_MODES = ["なし", "ふりがな", "かなのみ"]

# --- Difficulty Settings ---
DIFFICULTY_SCALES = {
    "Japanese": ["N5 (Beginner)", "N4 (Elementary)", "N3 (Intermediate)", "N2 (Pre-Advanced)", "N1 (Advanced)"],
    "Chinese": ["HSK 1-2 (Beginner)", "HSK 3 (Elementary)", "HSK 4 (Intermediate)", "HSK 5 (Pre-Advanced)", "HSK 6 (Advanced)"],
    "Korean": ["TOPIK 1 (Beginner)", "TOPIK 2 (Elementary)", "TOPIK 3 (Intermediate)", "TOPIK 4 (Pre-Advanced)", "TOPIK 5-6 (Advanced)"],
    "Spanish": ["A1 (Beginner)", "A2 (Elementary)", "B1 (Intermediate)", "B2 (Upper Intermediate)", "C1-C2 (Advanced)"],
    "French": ["A1 (Beginner)", "A2 (Elementary)", "B1 (Intermediate)", "B2 (Upper Intermediate)", "C1-C2 (Advanced)"],
    "Italian": ["A1 (Beginner)", "A2 (Elementary)", "B1 (Intermediate)", "B2 (Upper Intermediate)", "C1-C2 (Advanced)"],
    "English": ["A1 (Beginner)", "A2 (Elementary)", "B1 (Intermediate)", "B2 (Upper Intermediate)", "C1-C2 (Advanced)"]
}

DIFFICULTY_PROMPT_MODIFIERS = {
    "Beginner": "VOCABULARY: Very simple, high-frequency words. SENTENCES: Short, simple syntax. GRAMMAR: Strictly basic tenses and structures. Avoid complex conjugation.",
    "Elementary": "VOCABULARY: Common everyday words. SENTENCES: Simple to compound sentences. GRAMMAR: Foundational grammar structures.",
    "Intermediate": "VOCABULARY: Varied everyday and situational vocabulary. SENTENCES: Compound and basic complex sentences. GRAMMAR: Moderate complexity.",
    "Pre-Advanced": "VOCABULARY: Broad range of vocabulary, including some idioms. SENTENCES: Complex syntax. GRAMMAR: Advanced structures allowed.",
    "Advanced": "VOCABULARY: Native-level, unrestricted. Use idioms and nuanced words. SENTENCES: Highly complex and completely natural. GRAMMAR: Full, unrestricted grammatical range."
}

# --- Scenarios ---
SCENARIOS = {
    "Restaurant": {
        "title": "Ordering at a Restaurant",
        "user_role": "Customer",
        "ai_role": "Waiter",
        "user_goal": "Order a random dish.",
        "goal": "The user must order a specific dish. (Asking for recommendations or asking what is on the menu is NOT ordering. They must explicitly place an order).",
        "start_instruction": "Welcome the customer and politely ask if they have decided on their order. If the target language is Japanese, you MUST say exactly: 'いらっしゃいませ。ご注文はお決まりですか？'",
        "persona_instruction": "You are a professional waiter. Speak ONLY in natural, polite customer service language appropriate for the target language (e.g. Keigo in Japanese, formal 'usted' in Spanish). Do NOT use casual language. Keep your responses short.",
        "cached_intros": {
            "Japanese": ["いらっしゃいませ。ご注文はお決まりですか？", "いらっしゃいませ。何になさいますか？", "いらっしゃいませ。メニューはお決まりでしょうか？"],
            "Spanish": ["¡Bienvenido! ¿Ya sabe qué va a pedir?", "Hola, buenas. ¿Le tomo nota?", "¡Buenas tardes! ¿Qué le gustaría comer?"],
            "French": ["Bienvenue ! Avez-vous choisi ?", "Bonjour, que désirez-vous ?", "Bonjour ! Vous avez fait votre choix ?"],
            "Italian": ["Benvenuto! Ha già deciso cosa ordinare?", "Buongiorno! Cosa vi porto?", "Salve, avete già scelto?"],
            "Chinese": ["欢迎光临！您点好菜了吗？", "您好，请问需要点什么？", "欢迎光临，想吃点什么？"],
            "Korean": ["어서 오세요. 주문하시겠어요?", "어서 오세요. 무엇을 주문하시겠습니까?", "주문 도와드릴까요?"],
            "English": ["Welcome! Have you decided on your order?", "Hi there! What can I get for you today?", "Good evening! Are you ready to order?"]
        }
    },
    "Classroom": {
        "title": "New Class Introduction",
        "user_role": "New Student",
        "ai_role": "Teacher",
        "user_goal": "Introduce your name, age, hobby, and end with a greeting.",
        "goal": "The user must introduce their name, age, AND hobby, and end with a greeting. (They must provide ALL 4 pieces of information).",
        "start_instruction": "Warmly introduce the new student to the class and ask them to introduce themselves. If the target language is Japanese, you MUST say exactly: '新しい生徒を紹介します。自己紹介をお願いします。'",
        "persona_instruction": "You are a friendly teacher. Speak politely but warmly and naturally to your students. Keep your responses short.",
        "cached_intros": {
            "Japanese": ["新しい生徒を紹介します。自己紹介をお願いします。", "皆さん、新しいクラスメイトです。自己紹介をお願いできますか？", "今日から一緒に勉強する新しい生徒です。自己紹介をどうぞ！"],
            "Spanish": ["Les presento al nuevo estudiante. ¿Podrías presentarte, por favor?", "¡Clase, tenemos un estudiante nuevo! Por favor, preséntate.", "Quiero presentarles a su nuevo compañero. Adelante, preséntate."],
            "French": ["Je vous présente notre nouvel élève. Peux-tu te présenter ?", "Bonjour à tous, voici notre nouveau camarade. Vas-y, présente-toi.", "Voici un nouvel étudiant dans notre classe. Je te laisse te présenter."],
            "Italian": ["Vi presento il nuovo studente. Puoi presentarti, per favore?", "Classe, ecco il nostro nuovo compagno. Prego, presentati.", "Un caloroso benvenuto al nuovo alunno. Presentati pure alla classe."],
            "Chinese": ["给大家介绍一下新同学。请你做个自我介绍吧。", "这是我们班的新同学。请做一下自我介绍。", "大家欢迎新同学！请开始你的自我介绍。"],
            "Korean": ["새로운 학생을 소개합니다. 자기소개 부탁해요.", "우리 반에 새로 온 친구예요. 자기소개 해볼까요?", "여러분, 새 친구가 왔어요. 자기소개 부탁합니다."],
            "English": ["Everyone, we have a new student joining us today. Please introduce yourself!", "Class, please welcome our new classmate. Go ahead, introduce yourself.", "I'd like to introduce our new student. Please tell us a little about yourself!"]
        }
    },
    "Shopping": {
        "title": "Buying Clothes",
        "user_role": "Customer",
        "ai_role": "Shop Clerk",
        "user_goal": "Ask for a different size of clothing and buy it.",
        "goal": "The user must ask if a different size is available. You must say yes and offer it. Then, the user must explicitly say they will buy it. Do NOT append [GOAL_REACHED] until they explicitly declare they are buying it.",
        "start_instruction": "Welcome the customer and ask if they are looking for anything specific. If the target language is Japanese, you MUST say exactly: 'いらっしゃいませ。何かお探しですか？'",
        "persona_instruction": "You are a polite retail shop clerk. Speak ONLY in natural, polite customer service language appropriate for the target language (e.g. Keigo in Japanese). Keep your responses short.",
        "cached_intros": {
            "Japanese": ["いらっしゃいませ。何かお探しですか？", "いらっしゃいませ。サイズ違いなどございましたらお声がけください。", "いらっしゃいませ。何かお手伝いしましょうか？"],
            "Spanish": ["¡Hola! ¿Busca algo en particular?", "Bienvenido, ¿le puedo ayudar en algo?", "Hola, ¿necesita ayuda con alguna talla?"],
            "French": ["Bonjour ! Vous cherchez quelque chose en particulier ?", "Bienvenue ! Je peux vous aider ?", "Bonjour, avez-vous besoin d'aide avec les tailles ?"],
            "Italian": ["Buongiorno! Cerca qualcosa in particolare?", "Benvenuto, posso aiutarla?", "Salve, ha bisogno di aiuto per le taglie?"],
            "Chinese": ["欢迎光临！您在找什么特别的款式吗？", "您好，需要帮忙找尺码吗？", "欢迎光临，需要我为您推荐吗？"],
            "Korean": ["어서 오세요. 찾으시는 거 있으신가요?", "어서 오세요. 사이즈 찾아드릴까요?", "무엇을 도와드릴까요?"],
            "English": ["Welcome in! Are you looking for anything in particular?", "Hi there! Let me know if you need help with any sizes.", "Welcome! Can I help you find anything today?"]
        }
    },
    "Directions": {
        "title": "Asking for Directions",
        "user_role": "Tourist",
        "ai_role": "Local",
        "user_goal": "Ask how to get to the train station and thank them.",
        "goal": "The user must ask for directions to the train station. You must give them directions. Then, the user must explicitly thank you. Do NOT append [GOAL_REACHED] until they explicitly thank you for the directions.",
        "start_instruction": "Notice the tourist looking lost and politely ask if they need help. If the target language is Japanese, you MUST say exactly: 'どうかしましたか？道に迷いましたか？'",
        "persona_instruction": "You are a helpful local citizen. Speak politely and naturally to a stranger. Keep your responses short.",
        "cached_intros": {
            "Japanese": ["どうかしましたか？道に迷いましたか？", "大丈夫ですか？何かお探しですか？", "何かお困りですか？"],
            "Spanish": ["¿Se encuentra bien? ¿Se ha perdido?", "¿Necesita ayuda? Parece perdido.", "Hola, ¿está buscando algo?"],
            "French": ["Ça va ? Vous êtes perdu ?", "Vous avez besoin d'aide ? Vous cherchez votre chemin ?", "Bonjour, je peux vous aider à trouver quelque chose ?"],
            "Italian": ["Tutto bene? Si è perso?", "Ha bisogno di aiuto? Sembra che si sia perso.", "Salve, cerca un posto in particolare?"],
            "Chinese": ["您好，迷路了吗？需要帮忙吗？", "您看起来好像迷路了，要去哪儿吗？", "你好，需要帮忙指路吗？"],
            "Korean": ["무슨 일 있으신가요? 길을 잃으셨나요?", "도와드릴까요? 길을 찾고 계신가요?", "괜찮으세요? 어디 찾으시는 곳이라도?"],
            "English": ["Are you alright? You look a little lost.", "Do you need a hand finding something?", "Hi there, can I help you find your way?"]
        }
    },
    "Convenience Store": {
        "title": "Convenience Store Checkout",
        "user_role": "Customer",
        "ai_role": "Cashier",
        "user_goal": "State whether you need a plastic bag, then pay.",
        "goal": "The user must state if they need a plastic bag. You must then ask for payment. Finally, the user must explicitly say they are paying (e.g. 'I will pay by card' or 'Here is the cash'). Do NOT append [GOAL_REACHED] until they explicitly pay.",
        "start_instruction": "Welcome the customer and ask if they need a plastic bag for their items. If the target language is Japanese, you MUST say exactly: 'いらっしゃいませ。レジ袋はご利用ですか？'",
        "persona_instruction": "You are a fast-paced convenience store cashier. Speak ONLY in standard customer service language appropriate for the target language (e.g. Keigo in Japanese). Keep your responses short.",
        "cached_intros": {
            "Japanese": ["いらっしゃいませ。レジ袋はご利用ですか？", "いらっしゃいませ。袋はお付けしますか？", "いらっしゃいませ。お持ち帰り用の袋は必要でしょうか？"],
            "Spanish": ["Hola. ¿Va a querer bolsa?", "Buenos días, ¿necesita una bolsa para sus cosas?", "¿Le pongo todo en una bolsa?"],
            "French": ["Bonjour. Avez-vous besoin d'un sac ?", "Bonjour, voulez-vous un sac en plastique ?", "Je vous donne un sac ?"],
            "Italian": ["Salve. Ha bisogno di un sacchetto?", "Buongiorno, vuole un sacchetto per la spesa?", "Le serve una busta?"],
            "Chinese": ["欢迎光临。请问需要塑料袋吗？", "您好，需要买个袋子吗？", "欢迎光临，请问要装袋吗？"],
            "Korean": ["어서 오세요. 봉투 필요하신가요?", "어서 오세요. 담아드릴 봉투 드릴까요?", "봉투에 담아드릴까요?"],
            "English": ["Hi there! Do you need a plastic bag for your items?", "Hello! Would you like a bag with that?", "Welcome! Will you be needing a bag today?"]
        }
    }
}