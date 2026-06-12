# Polyglot AI Tutor

A modern, full-stack AI language learning web application. It features a React frontend and a FastAPI backend, leveraging advanced Text-to-Speech (TTS) engines like Style-Bert-VITS2, MeloTTS, CosyVoice2, and Microsoft Edge-TTS to provide ultra-realistic speech synthesis in Japanese, Chinese, Korean, Spanish, French, and Italian.

## Features

- **AI Conversation** — Chat with an AI tutor in your target language with automatic text-to-speech responses.
- **Interactive Scenarios** — Practice real-world situations (e.g., Ordering at a Restaurant, Asking for Directions) with guided AI interactions.
- **Multi-Language TTS** — Natural speech synthesis powered by Style-Bert-VITS2 (Japanese), MeloTTS (European), CosyVoice2 (Chinese/Korean), and Edge-TTS.
- **Word Dictionary & Translation** — Highlight any word or phrase in the chat to instantly see its translation and reading.
- **Vocabulary Notebook** — Save highlighted words to a personal notebook for future review.
- **Grammar & Pronunciation Feedback** — Receive inline grammar corrections and pronunciation hints from the AI tutor.
- **Replay Controls** — Replay full messages or partial highlighted text at adjustable speeds to practice listening.
- **Speech-to-Text (STT)** — Hands-free voice-to-voice practice using browser microphone APIs.

## Tech Stack

- **Frontend:** React, Vite, Tailwind CSS, Framer Motion
- **Backend:** Python, FastAPI, WebSockets, SQLAlchemy (PostgreSQL / SQLite)
- **AI/TTS:** OpenAI/vLLM API, Style-Bert-VITS2, MeloTTS, CosyVoice2, Edge-TTS

## Getting Started

### 1. Configure Environment

Create a `.env` file in the project root to configure your API keys. If deploying via Docker, refer to `.env.spark.example`:

```env
OPENAI_API_KEY=your_api_key_here
```

### 2. Run the Backend (FastAPI)

You can run the backend natively or via Docker.

**Note on TTS Models:**
The backend uses large TTS models (Style-Bert-VITS2, MeloTTS, CosyVoice2) that are **automatically downloaded** from Hugging Face on their first use. If running via Docker, these are cached in a persistent volume (`hf_cache`).

**Native (Requires Python 3.11+):**
```bash
pip install -r requirements.txt
python main.py
```
The backend will run on `http://localhost:8081`.

**Docker:**
```bash
docker build -t polyglot-backend -f backend.Dockerfile .
docker run -p 8081:8081 -v polyglot_hf_cache:/root/.cache/huggingface --env-file .env polyglot-backend
```

### 3. Run the Frontend (React)

Open a new terminal and navigate to the `frontend` directory:

```bash
cd frontend
npm install
npm run dev
```

Navigate to `http://localhost:3000` (or the port provided by Vite) in your browser.

## Key Architecture

- **WebSockets:** The chat interface uses real-time WebSockets to stream AI responses, audio chunks, and grammar corrections concurrently for zero latency.
- **Frontend Components:** The React UI is modularized (e.g., `ChatUI`, `MessageList`, `Sidebar`) and memoized for optimal rendering performance when streaming text.
- **Audio Queue:** Audio binary data is streamed via WebSockets and played seamlessly using a custom Web Audio API queue.
