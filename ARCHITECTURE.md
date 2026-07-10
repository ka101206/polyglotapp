# Polyglot AI Tutor — Architecture Overview

A full-stack, self-hosted AI language-learning app. A React SPA talks to a FastAPI
backend over REST + WebSockets. The backend orchestrates a local LLM (via a
vLLM/OpenAI-compatible endpoint) for conversation, grammar analysis, and translation,
and a stack of neural TTS engines for speech synthesis. State lives in PostgreSQL
(pgvector). Everything is wired together with Docker Compose behind an nginx proxy.

## High-level diagram

```
                              Host port 8080
                                    │
                          ┌─────────▼──────────┐
                          │   nginx  (proxy)   │   ./nginx.conf
                          │  polyglot-spark-   │
                          │       proxy        │
                          └───┬────────────┬───┘
             /  (SPA + HMR)   │            │  /api/  +  /ws/
                              │            │
                    ┌─────────▼───┐   ┌────▼──────────────────┐
                    │  frontend   │   │       backend         │
                    │ Vite+React  │   │  FastAPI / uvicorn    │
                    │  :3000      │   │  :8081                │
                    └─────────────┘   └───┬───────────────┬───┘
                                          │               │
                                 ┌────────▼─────┐  ┌───────▼────────────┐
                                 │ PostgreSQL   │  │ vLLM / OpenAI API  │
                                 │ (pgvector)   │  │ host.docker.internal│
                                 │  :5432       │  │      :8000/v1       │
                                 └──────────────┘  └────────────────────┘
                                          + TTS engines (SBV2/Melo/CosyVoice/Edge)
                                            & STT (SpeechRecognition) in-process
```

## Services (docker-compose.yml)

| Service    | Container                | Image / Build            | Host port | Role |
|------------|--------------------------|--------------------------|-----------|------|
| `proxy`    | `polyglot-spark-proxy`   | `nginx:alpine`           | **8080**→80 | Single entrypoint; routes `/` to frontend, `/api/` & `/ws/` to backend |
| `frontend` | `polyglot-spark-frontend`| `frontend.Dockerfile`    | internal :3000 | Vite dev server (React + Tailwind v4), HMR over WS |
| `backend`  | `polyglot-spark-backend` | `backend.Dockerfile`     | 18082→8081 | FastAPI app; AI orchestration, TTS/STT, persistence |
| `db`       | `polyglot-spark-db`      | `pgvector/pgvector:pg16` | internal :5432 | PostgreSQL with pgvector; app data |

External dependency: a **vLLM server** (OpenAI-compatible) reached at
`host.docker.internal:8000/v1`, model `qwen2.5-7b-fp8` by default. The backend also
reaches Hugging Face on first run to download TTS models, cached in the `hf_cache` volume.

Volumes: `polyglot_spark_pgdata` (Postgres data), `hf_cache` (downloaded TTS model weights).
Network: all services share the `polyglot-spark` bridge network and address each other by
service name (`backend`, `frontend`, `db`).

## Backend (`/`, FastAPI — Python 3.11)

Entry point `main.py` (~800 lines). Key modules:

- **`main.py`** — FastAPI app, routes, and the core chat WebSocket.
- **`ai_client.py`** — `AIClient` class: all LLM interaction. Streams sentence-by-sentence
  replies, maintains conversation history (with periodic compaction), formality detection,
  grammar correction/analysis, word-bank generation, definitions, and scenario dialogue.
- **`database.py`** — SQLAlchemy models + session management (Postgres in prod, SQLite fallback).
- **`config.py`** — Supported languages, difficulty levels, and scenario definitions.
- **`analytics.py`** — Aggregates per-user learning metrics.
- **TTS engines** — `tts_engine.py` (dispatcher) + `tts_sbv2.py` (Style-Bert-VITS2, Japanese),
  `tts_melo.py` (MeloTTS, European), `tts_cosyvoice.py` (CosyVoice2, Chinese/Korean),
  `tts_chatterbox.py`, plus Edge-TTS. Language determines the engine.
- **`stt_engine.py`** — Speech-to-text via `SpeechRecognition`.
- **`audio_comparison.py`** — Pronunciation scoring (librosa + fastdtw/DTW).

### Real-time chat WebSocket — ` /ws/chat/{user_id}`

The heart of the app. Over a single socket the backend concurrently streams:
1. **AI reply text**, sentence-by-sentence as the LLM generates it.
2. **Audio chunks** — each sentence is synthesized and pushed as binary frames for
   gap-free playback via a Web Audio queue on the client.
3. **Grammar corrections / word-bank / reading annotations** (e.g. furigana, pinyin).

Reading modes post-process text per language (romaji stripping, furigana, etc.).

### REST endpoints (`/api/`, `/auth/`)

- **Auth & users** — `POST /auth/register`, `POST /auth/login` (bcrypt), `PUT /api/users/{id}`,
  `DELETE /api/users/{id}`.
- **Admin / groups** — create/delete groups, assign users, invites, per-user setting overrides
  (forced language/difficulty/reading mode, low-token mode), session inspection.
- **Notebook / SRS** — `GET/POST /api/notebook`, `GET /api/notebook/review`,
  `POST /api/notebook/review/{id}` — spaced-repetition vocabulary (SM-2: interval,
  ease factor, repetitions, next-review date).
- **AI utilities** — `POST /api/ai/definition`, `POST /api/audio/transcribe`.
- **Analytics** — `GET /api/analytics/{user_id}`.
- **Health** — `GET /health` (used by the compose healthcheck).

## Data model (`database.py`)

- **User** — credentials, avatar, speaking stats (`avg_chars_per_second`, totals), admin flag,
  group membership, and per-user forced overrides.
- **Group** / **GroupInvite** — classroom-style grouping with an admin and pending invites.
- **ConversationSession** → **Message** — chat history grouped into sessions, each with an
  AI-generated summary; messages tagged `User` / `AI` / `System`.
- **Vocabulary** — saved words + SRS scheduling fields (interval, ease_factor, repetitions,
  next_review_date).
- **Analytic** — daily per-user aggregates (speaking time, mistakes, running sums/counts for
  fluency, grammar, listening, and pronunciation scores).

## Frontend (`/frontend`, React 19 + Vite 8 + Tailwind v4)

SPA served by the Vite dev server (`--host 0.0.0.0 --port 3000`, HMR proxied through nginx).

- **`App.jsx`** — top-level router/state.
- **`ChatUI.jsx`** — main conversation view.
- **`components/`** — `MessageList`, `ChatInput`, `Sidebar`, `SettingsModal`, `Popups`,
  `SRSReviewModal` (memoized for smooth streaming).
- **`hooks/`** — `useChatWebSocket.js` (chat socket + audio queue), `useMicrophone.js` (mic capture).
- **Other views** — `Auth.jsx`, `AdminDashboard.jsx`, `AnalyticsDashboard.jsx`, `Inbox.jsx`,
  `LanguageSelect.jsx`, `ErrorBoundary.jsx`.
- Vite proxies `/api`, `/auth`, `/ws` to `backend:8081` (also handled by nginx in the compose stack).

## Request flow (a spoken turn)

1. User speaks → `useMicrophone` captures audio → `POST /api/audio/transcribe` (STT) →
   transcript.
2. Client sends transcript over `/ws/chat/{user_id}`.
3. Backend calls `AIClient.get_reply_stream()` → streams sentences from the vLLM LLM.
4. Each sentence is synthesized by the language-appropriate TTS engine → binary audio frames
   over the same socket.
5. In parallel, grammar analysis + word-bank + reading annotations stream back.
6. Client renders text incrementally and plays audio via the Web Audio queue.
7. Messages, vocab, and analytics are persisted to Postgres.

## Configuration & deployment

- Config via `.env` (see `.env.example`). Notable keys: `POLYGLOT_FRONTEND_PORT` (default 8080),
  `POLYGLOT_BACKEND_PORT` (18082), `POLYGLOT_PUBLIC_API_URL`, DB credentials, `POLYGLOT_VLLM_URL`,
  `POLYGLOT_AI_MODEL`, `POLYGLOT_OPENAI_API_KEY`.
- Build & run: `docker compose up -d --build`.
- Access on this host: `http://localhost:8080`. For remote/Tailscale access notes see
  `/home/aboveavg/CLAUDE.md`.

## Tech stack summary

- **Frontend:** React 19, Vite 8, Tailwind CSS v4, Framer Motion, lucide-react, react-router-dom.
- **Backend:** FastAPI, uvicorn, WebSockets, SQLAlchemy 2, bcrypt.
- **AI:** vLLM / OpenAI-compatible API (Qwen2.5-7B by default).
- **TTS:** Style-Bert-VITS2, MeloTTS, CosyVoice2, Edge-TTS.
- **STT / audio:** SpeechRecognition, librosa, fastdtw, soundfile, ffmpeg/espeak-ng.
- **Data:** PostgreSQL (pgvector:pg16).
- **Infra:** Docker Compose, nginx reverse proxy.
