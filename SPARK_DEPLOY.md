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

Before building, place the TTS model assets in the project directory:

```text
kokoro-v1.0.onnx
voices.bin
models/es_ES-sharvard-medium.onnx
models/fr_FR-tom-medium.onnx
models/it_IT-riccardo-x_low.onnx
```

The provided `download_models.sh` downloads them, but it requires outbound network
access:

```bash
./download_models.sh
```

The Spark compose file mounts these files into the backend read-only at runtime. They are
not copied into the Docker image and are intentionally ignored by git. If
`kokoro-v1.0.onnx` or `voices.bin` is missing, `docker compose up` fails instead of
starting a backend with broken Japanese TTS.

Japanese TTS needs `kokoro-v1.0.onnx` and `voices.bin`. Edge TTS and Google STT also
require outbound internet at runtime.

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
