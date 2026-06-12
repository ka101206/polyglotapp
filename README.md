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

Create a `.env` file in the project root by copying the example:

```bash
cp .env.example .env
```

Edit the `.env` file and set your desired `POLYGLOT_DB_PASSWORD` and `OPENAI_API_KEY` (if not using vLLM).

### 2. Deploy via Docker

The entire application (Database, Backend, and Frontend) runs seamlessly on Docker. 

**Note on TTS Models:**
The backend uses large TTS models (Style-Bert-VITS2, MeloTTS, CosyVoice2) that are **automatically downloaded** from Hugging Face on their first use. These are cached in a persistent volume (`hf_cache`) so they do not need to be redownloaded on restart.

Run the following command to build and deploy all services:
```bash
docker compose up -d --build
```

The application will be accessible at `http://localhost:18080` (or your host IP address at port 18080).

## Key Architecture

- **WebSockets:** The chat interface uses real-time WebSockets to stream AI responses, audio chunks, and grammar corrections concurrently for zero latency.
- **Frontend Components:** The React UI is modularized (e.g., `ChatUI`, `MessageList`, `Sidebar`) and memoized for optimal rendering performance when streaming text.
- **Audio Queue:** Audio binary data is streamed via WebSockets and played seamlessly using a custom Web Audio API queue.
