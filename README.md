# RAG Document System

Production-ready Retrieval-Augmented Generation (RAG) service for PDF documents.

- **backend/** — Python 3.11 + FastAPI. Upload PDFs, chunk + embed with Azure OpenAI, store in Cosmos DB, retrieve semantically, answer with GPT.
- **upload-ui/** — React + Vite. Drag-and-drop PDF upload, polling document list with status/size, delete.
- **query-ui/** — React + Vite. Ask a question; shows the answer with the source chunks (document + page).
- **deployment/** — Docker Compose, nginx reverse proxy on port 8080, self-signed cert generator.
- **.github/workflows/deploy.yml** — SSH deploy to a Linux VM.

## Architecture

```
Browser ──▶ nginx (:8080) ──▶ upload-ui / query-ui  (static)
                       └───▶ FastAPI backend ──▶ Azure Blob / Cosmos DB / Azure OpenAI
```

## API

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/health` | Liveness — always returns fast |
| POST   | `/api/upload` | multipart upload of a PDF |
| GET    | `/api/documents` | List with `file_size`, `status`, `chunks_count` |
| DELETE | `/api/documents/{id}` | Remove blob + Cosmos entry |
| POST   | `/api/query` | `{question}` → `{answer, sources[]}` |

## Environment variables

All are **required**. The backend validates every one of them at startup and
fails fast, naming the missing/malformed variable. `AZURE_OPENAI_ENDPOINT` and
`COSMOS_DB_ENDPOINT` are additionally URL-parsed so a mispasted secret fails at
boot instead of during a request.

| Name | Purpose |
|------|---------|
| `AZURE_STORAGE_ACCOUNT_NAME` | Blob account, e.g. `ragsysstore01` |
| `AZURE_STORAGE_ACCOUNT_KEY` | Blob account key |
| `AZURE_STORAGE_CONTAINER_NAME` | Blob container, e.g. `documents` |
| `COSMOS_DB_ENDPOINT` | Cosmos endpoint URL |
| `COSMOS_DB_KEY` | Cosmos primary key |
| `COSMOS_DB_NAME` | Database name, e.g. `ragdb` |
| `COSMOS_DB_CONTAINER_NAME` | Container name, e.g. `documents` |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI URL |
| `AZURE_OPENAI_KEY` | Azure OpenAI key |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Chat deployment, e.g. `gpt-4.1-mini` |
| `AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS_NAME` | Embeddings deployment, e.g. `text-embedding-ada-002` |
| `AZURE_OPENAI_API_VERSION` | API version, e.g. `2024-06-01` |

Optional tunables: `EMBEDDING_BATCH_SIZE` (default 16), `CHUNK_SIZE_CHARS`
(1200), `CHUNK_OVERLAP_CHARS` (150), `TOP_K` (5).

## Local development

```bash
cd deployment
./generate-certs.sh
# create .env in this directory with the twelve variables above
docker compose --env-file .env config    # sanity check — no value should be empty
docker compose --env-file .env up --build
```

Open http://localhost:8080/ for upload, http://localhost:8080/query/ for query.

## GitHub Actions deployment

The workflow `.github/workflows/deploy.yml` deploys on push to `main` (or via
`workflow_dispatch`). Required repository secrets:

- `SERVER_HOST` — e.g. `103.216.171.67`
- `SERVER_USER` — e.g. `root`
- `SERVER_SSH_KEY` — private key contents, key-only auth
- All twelve Azure environment variables listed above.

The workflow:

1. rsyncs the repo to `/opt/rag-system/`.
2. Writes `.env` **next to `docker-compose.yml`** (Compose resolves `.env`
   from the compose file's directory, not the working directory).
3. Generates self-signed certs (idempotent).
4. Runs `docker compose config` and fails if any environment value renders
   empty.
5. `docker compose up -d --build`.
6. Polls `http://127.0.0.1:8080/health` for up to 60s; fails otherwise.

## Correctness invariants

These are enforced in code / config:

1. Compose `.env` lives beside `docker-compose.yml`; the workflow places it
   there and passes `--env-file` explicitly.
2. Azure resources are provisioned defensively via
   `create_database_if_not_exists`, `create_container_if_not_exists`
   (partition key `/id`), and blob `create_container` catching
   `ResourceExistsError`.
3. Cosmos SQL uses parameterised `OFFSET 0 LIMIT @n`, never a bare `LIMIT`.
4. `replace_item(item=doc_id, body=doc)` is always called with both args.
5. Every field in `DocumentSummary` is written on document create; optional
   fields have defaults so a single malformed record does not fail the list
   endpoint.
6. Background PDF processing is a plain `def` given to
   `BackgroundTasks.add_task`, which Starlette runs in a threadpool; Blob and
   Cosmos calls made from async handlers use `asyncio.to_thread`. `/health`
   stays fast even while a large PDF is embedding.
7. Retrieval embeds the query and cosine-ranks against every stored chunk
   embedding, returning top N.
8. nginx sets `absolute_redirect off` so redirects don't strip port 8080.
9. nginx sets `proxy_read_timeout 300s` and `client_max_body_size 100M` on
   API routes.
10. nginx uses `resolver 127.0.0.11 valid=10s` with variables in `proxy_pass`
    so it starts even when an upstream container is briefly down.
11. Embeddings are batched (`EMBEDDING_BATCH_SIZE`); HTTP 429 triggers
    bounded exponential backoff (max 6 retries) — after that, the document
    is marked `failed` with a clear message.
12. The deploy workflow never embeds credentials in git URLs; it uses rsync
    over SSH with a key.
