# Deploying Polyglot to polyglotlearning.com (Cloudflare + VPS + OpenRouter)

This is the production deploy for the `feature/cloudflare-deploy` branch. It runs
the same Docker Compose stack (db / backend / frontend / nginx proxy) on a public
VPS, with Cloudflare in front for TLS + DNS, and OpenRouter as the LLM backend
(no DGX / no local vLLM).

## 0. What you need
- A VPS: ~4–8 GB RAM, 2+ vCPU, ~40 GB disk, Ubuntu 24.04. Note its public IPv4.
- An OpenRouter API key (`sk-or-...`).
- The domain `polyglotlearning.com` in your Cloudflare account.

## 1. Prepare the VPS
```bash
ssh root@YOUR_VPS_IP
ufw allow 22 && ufw allow 80 && ufw allow 443 && ufw enable
curl -fsSL https://get.docker.com | sh          # Docker + Compose v2
```
Use SSH keys and disable password login before going live.

## 2. Get the code
```bash
git clone <your-repo-url> polyglotapp
cd polyglotapp
git checkout feature/cloudflare-deploy
```

## 3. Configure secrets
```bash
cp .env.production.example .env
# edit .env: set POLYGLOT_DB_PASSWORD, POLYGLOT_OPENAI_API_KEY (sk-or-...),
# and confirm POLYGLOT_AI_MODEL (default: google/gemini-2.5-flash-lite).
```

## 4. DNS in Cloudflare
Cloudflare dashboard → **DNS** → add two records (both **Proxied / orange cloud**):
- `A`  `@`   → `YOUR_VPS_IP`
- `A`  `www` → `YOUR_VPS_IP`

## 5. TLS (Cloudflare → origin)
Pick one, in Cloudflare → **SSL/TLS**:
- **Recommended:** *Origin Server → Create Certificate*. Save the cert/key over
  `nginx-selfsigned.crt` / `nginx-selfsigned.key`, then set the mode to
  **Full (strict)**.
- **Quick:** leave the bundled self-signed cert and set the mode to **Full**.

Do **not** use *Flexible* (redirect loops + insecure).

## 6. Launch
```bash
docker compose up -d --build      # first build bakes ~3 GB of TTS models; be patient
docker compose ps                 # all four services should be healthy
```

## 7. WebSockets (conversation mode)
- Cloudflare → **Network → WebSockets: On** (default; verify).
- The keepalive heartbeat is already in the code (30s client ping / server pong,
  plus a raised nginx `proxy_read_timeout`) so conversation mode survives
  Cloudflare's ~100s idle cutoff during pauses.

## 8. Verify
Open `https://polyglotlearning.com`:
- page loads over a valid cert (padlock),
- microphone permission works (real cert = secure context),
- a full conversation turn streams text + audio,
- `docker compose logs -f backend` is clean.

## 9. Before you monetize / go fully public
The site is world-reachable with an OpenRouter-billed backend and CORS `*`:
- Add **rate limiting** on the API + WS endpoints (protect your OpenRouter spend).
- Keep the DGX-only bits unused (VLLM_URL now points at OpenRouter).
- Consider Cloudflare **WAF / rate-limiting rules** and optionally **Access** if
  you want a login gate during beta.

## Switching the LLM model (at will, no restart)
The active model lives in **`llm_config.json`** (bind-mounted into the backend).
To change it, edit the file on the server and save — the app re-reads it live:
```bash
# on the VPS, in the project dir
nano llm_config.json          # set "model" to any OpenRouter slug, save
curl -s localhost:18082/api/llm/model   # confirm the active model changed
```
No restart, no rebuild. `available` in that file is just a reference list of
vetted picks. If the file is missing or the model is blank, it falls back to
`POLYGLOT_AI_MODEL` from `.env`.

## Updating later
```bash
git pull
docker compose up -d --build
```
