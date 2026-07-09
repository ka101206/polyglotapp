# Polyglot AI Tutor

A modern, full-stack AI language-learning web application. It features a React
frontend and a FastAPI backend, leveraging a local LLM (via a vLLM/OpenAI-compatible
endpoint) for conversation and neural Text-to-Speech (Style-Bert-VITS2, with Edge-TTS
fallback) for ultra-realistic speech synthesis in Japanese, Chinese, Korean, Spanish,
French, and Italian.

## Features

- **AI Conversation** — Chat with an AI tutor in your target language with automatic text-to-speech responses.
- **Interactive Scenarios** — Practice real-world situations (e.g., Ordering at a Restaurant, Asking for Directions) with guided AI interactions.
- **Multi-Language TTS** — Natural Japanese speech via Style-Bert-VITS2 (Koharune Ami / JVNV voices), with Microsoft Edge-TTS covering the other languages.
- **Word Dictionary & Translation** — Highlight any word or phrase in the chat to instantly see its translation and reading.
- **Vocabulary Notebook (SRS)** — Save highlighted words to a personal notebook with spaced-repetition review. Readings are language-appropriate: **furigana** for Japanese, **pinyin** for Chinese, and **Latin-alphabet romanization** for Korean.
- **Grammar & Pronunciation Feedback** — Receive inline grammar corrections and pronunciation hints from the AI tutor.
- **Replay Controls** — Replay full messages or partial highlighted text at adjustable speeds to practice listening.
- **Speech-to-Text (STT)** — Hands-free voice-to-voice practice using browser microphone APIs.
- **Admin & Groups** — Classroom-style groups, invites, and per-user setting overrides (forced language/difficulty/reading mode, low-token mode).

## Tech Stack

- **Frontend:** React 19, Vite, Tailwind CSS v4, Framer Motion
- **Backend:** Python, FastAPI, WebSockets, SQLAlchemy (PostgreSQL / pgvector)
- **LLM:** vLLM / OpenAI-compatible API (default model `qwen3.6-35b-a3b`)
- **TTS:** Style-Bert-VITS2 (Japanese), Microsoft Edge-TTS (other languages)

## Getting Started

### 1. Configure Environment

Create a `.env` file in the project root by copying the example:

```bash
cp .env.example .env
```

Set at minimum `POLYGLOT_DB_PASSWORD`, and point `POLYGLOT_VLLM_URL` / `POLYGLOT_AI_MODEL`
at your LLM endpoint. The model name **must exactly match** a model served by your vLLM
instance (check the debug console — see below — if AI replies come back empty).

### 2. Deploy via Docker

The entire application (database, backend, frontend, and nginx proxy) runs on Docker Compose:

```bash
docker compose up -d --build
```

The app is served at **`http://localhost:8080`** (or your host IP / Tailscale IP at port 8080).

**TTS models are baked into the backend image at build time** (see `download_models.py`
and `backend.Dockerfile`), so there is **no runtime model download** — Japanese TTS is ready
the moment the container starts, and the container is self-contained / offline-capable.
Because the model layer is cached before the application code is copied, ordinary code
changes rebuild in seconds; only changing `tts_sbv2.py` re-downloads the models.

## Remote Access via Tailscale

The app is typically hosted on a development machine that isn't on your local
network, so you reach it over [Tailscale](https://tailscale.com) rather than a plain
LAN IP. Once connected, the app is at **`http://<tailscale-ip>:8080`**.

### ⚠️ The #1 gotcha: shared devices get a different IP in every tailnet

The host is usually **shared** into your tailnet from the owner's account. **A shared
device is assigned a *different* `100.x` address in each tailnet it's shared into.**
This is the most common reason people can't connect:

- The IP the **owner** sees (e.g. what `tailscale status` shows *on the host itself*)
  is **not** the IP **you** use.
- You must use the address **your own tailnet** assigned to the shared device.

**Find the right IP** — on your own machine, either:

```bash
tailscale status        # look for the shared host in the list; use ITS 100.x address
```

or open the [Tailscale admin console](https://login.tailscale.com/admin/machines) →
**Machines**, find the shared host, and copy the IP shown there. Then browse to
`http://<that-ip>:8080`.

### Troubleshooting checklist

1. **Is Tailscale actually connected?** Installing the app isn't enough — open it and
   toggle it **on**. Run `tailscale status` on your machine; if the host doesn't appear
   in the list, you're not connected to the right tailnet.
2. **Same tailnet/account?** Tailscale `100.x` IPs only work between devices on the
   *same* tailnet. Make sure you accepted the device share and are logged into the
   account it was shared with.
3. **Using the right (your-tailnet) IP?** See the gotcha above — not the owner's IP.
4. **Test reachability:** `tailscale ping <ip>` from your machine.
   - Ping works but the page hangs → a tailnet **ACL** may be blocking port 8080 for
     shared users (the owner needs to allow it).
   - Ping fails → the device share or authorization needs attention on the owner's side.
5. **Prefer the raw `100.x` IP over MagicDNS hostnames** — DNS resolution across a shared
   tailnet can be flaky; the numeric IP always works.

> The host also exposes the app on its local network at `http://<lan-ip>:8080`, so if you
> can get onto the *same* physical network as the host, Tailscale isn't required.

## Debug Console

A self-contained health dashboard is served **directly by the backend** (not the React
frontend), so it keeps working even when the frontend, Vite, or nginx are broken — making
it the first place to look when something misbehaves.

- **`http://<host>:18082/debug`** — direct to the backend (most robust; bypasses nginx/frontend)
- **`http://<host>:8080/debug`** — through the nginx proxy
- **`GET /api/debug/status`** — the underlying JSON (handy for scripting/monitoring)

It auto-refreshes every 5 seconds and reports:

| Check | What it verifies |
|-------|------------------|
| **PostgreSQL** | Database connectivity (`SELECT 1`) |
| **LLM (vLLM)** | Endpoint reachable **and** the configured model is actually served |
| **TTS — Japanese** | Style-Bert-VITS2 model files are present (baked in) / loaded |
| **Speech-to-Text** | STT library available |
| **Internet / Edge-TTS** | Outbound HTTPS works (required for the Edge-TTS fallback) |

It also shows a live **Active Connections** table listing every open WebSocket session —
role (admin/student), user, current language, message count, and connection/idle times —
so multiple accounts can be watched simultaneously while testing.

> Tip: if the AI returns nothing, open the debug console. A yellow **LLM** card that says
> the configured model is "NOT served" means `POLYGLOT_AI_MODEL` doesn't match a model name
> your vLLM instance is serving.

## Key Architecture

- **WebSockets:** The chat interface streams AI responses, audio chunks, and grammar corrections concurrently over a single WebSocket for minimal latency.
- **Reasoning-model handling:** The default LLM is a reasoning model; the client disables "thinking" and reads whichever field (`content` or `reasoning`) carries the reply, so small token budgets still produce answers.
- **Audio Queue:** Audio binary data is streamed via WebSockets and played seamlessly using a custom Web Audio API queue.
- **Frontend Components:** The React UI is modularized (`ChatUI`, `MessageList`, `Sidebar`, etc.) and memoized for smooth rendering while streaming.

See `ARCHITECTURE.md` for a full component-by-component breakdown.

## Service Ports

| Port | Service | Notes |
|------|---------|-------|
| **8080** | nginx proxy | Main entry point (frontend + `/api` + `/ws` + `/debug`) |
| 18082 | Backend (FastAPI) | Direct access; also serves `/debug` |
| — | Frontend (Vite) | Internal only (proxied) |
| — | PostgreSQL | Internal only |
