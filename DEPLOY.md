# Deploying Polyglot to polyglotlearning.com (Cloudflare + VPS + OpenRouter)

This is the production deploy for the `feature/cloudflare-deploy` branch. It runs
the Docker Compose stack (db / backend / frontend / nginx proxy) with Cloudflare
in front and OpenRouter as the LLM backend (no DGX / no local vLLM).

**Two hosting paths — pick one:**
- **A) Public VPS** (has a public IP): steps 1–9 below, using DNS A-records.
- **B) Home / NAT server** (behind a router, no public IP): steps 1–3, then the
  **"Home server (Cloudflare Tunnel)"** section *instead of* steps 4–5. This is
  the right choice for a machine at home — no port forwarding, no exposed IP.

## 0. What you need
- A server: ~8 GB RAM, 2+ vCPU, ~40 GB disk, Docker installed. (Public-IP VPS for
  path A; any home box already running Docker for path B.)
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

## 4. DNS in Cloudflare  *(path A — public VPS only)*
> Home / NAT server? **Skip steps 4–5** and jump to the "Home server (Cloudflare
> Tunnel)" section below.

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
# Path A (public VPS):
docker compose up -d --build          # first build bakes ~3 GB of TTS models; be patient

# Path B (home server via tunnel): include the cloudflared service
docker compose --profile tunnel up -d --build

docker compose ps                     # services should be healthy
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

## Home server (Cloudflare Tunnel) — path B, replaces steps 4–5
For a machine at home behind a router (no public IP), use a Cloudflare Tunnel.
cloudflared dials *out* to Cloudflare, so there's **no port forwarding, no open
inbound ports, and your home IP stays hidden**. Cloudflare still provides the
public HTTPS cert (so the mic works), and the tunnel leg is encrypted — the
origin can be plain HTTP, so **no self-signed cert is needed**.

Do steps 1–3 first (code + `.env`), then:

**1. Create the tunnel in Cloudflare**
- Cloudflare dashboard → **Zero Trust → Networks → Tunnels → Create a tunnel**.
- Type: **Cloudflared**. Name it (e.g. `polyglot-home`). **Save the token** it
  shows (a long string) — that's your `POLYGLOT_TUNNEL_TOKEN`.

**2. Add the public hostname → service mapping** (in that tunnel's config):
- Public hostname: `polyglotlearning.com`
- Service: **`http://proxy:80`**  ← the nginx proxy container on the Docker
  network (cloudflared shares the network, so it resolves `proxy` by name).
- Add a second hostname `www.polyglotlearning.com` → the same service if you want.

**3. Put the token in `.env`**
```dotenv
POLYGLOT_TUNNEL_TOKEN=eyJ...your-tunnel-token...
```

**4. Launch with the tunnel profile**
```bash
docker compose --profile tunnel up -d --build
docker compose logs -f cloudflared     # should show "Registered tunnel connection"
```

**5. TLS mode**: in Cloudflare → SSL/TLS, **Full** is fine (the tunnel encrypts
the origin leg). No Origin cert / no self-signed cert required for tunnels.

Notes:
- Host ports 80/443 are **not** required in this mode — the tunnel reaches the
  proxy internally, so it won't collide with other containers already on the box.
- WebSockets work through tunnels automatically; the keepalive heartbeat still
  applies. Then continue at step 7 (WebSockets) and step 8 (Verify).
- Uptime now depends on your home power + internet. Fine for beta/personal use.

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
