# Polyglot DGX Spark Deployment

This deployment is intentionally separate from `docker-compose.yml` so the original
local workflow remains unchanged.

## Ports

The Spark compose file avoids documented existing ports by default:

| Service | Container | Host port | Container port |
|---|---|---:|---:|
| Frontend | `polyglot-spark-frontend` | `18080` | `3000` |
| Backend | `polyglot-spark-backend` | `18082` | `8081` |
| Postgres | `polyglot-spark-db` | not exposed | `5432` |

User URL:

```text
http://10.74.10.244:18080
```

## Required Assets

The backend uses large TTS models (Style-Bert-VITS2, MeloTTS, CosyVoice2) that are automatically downloaded from Hugging Face the first time they are used. 

The `docker-compose.spark.yml` maps a persistent Docker volume (`hf_cache`) to `/root/.cache/huggingface` in the backend container so these models do not need to be redownloaded if the container restarts.

**Note:** The backend requires outbound internet access to download these models on their first run. Edge TTS and Google STT also require outbound internet access at runtime.

## Deploy

```bash
cp .env.spark.example .env.spark
# edit .env.spark and set POLYGLOT_DB_PASSWORD
docker compose --env-file .env.spark -f docker-compose.spark.yml build
docker compose --env-file .env.spark -f docker-compose.spark.yml up -d
```

## Verify

```bash
docker ps --filter name=polyglot-spark
curl http://127.0.0.1:18082/health
curl -I http://127.0.0.1:18080
```

From another machine on the LAN, open:

```text
http://10.74.10.244:18080
```

## Stop

```bash
docker compose --env-file .env.spark -f docker-compose.spark.yml down
```

Do not use `-v` unless you intentionally want to delete Polyglot user data.
