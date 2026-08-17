"""Configuration loaded and validated from environment variables.

Fails fast at import time if any required variable is missing or malformed.
"""
from __future__ import annotations

import os
from urllib.parse import urlparse


REQUIRED_VARS = [
    "AZURE_STORAGE_ACCOUNT_NAME",
    "AZURE_STORAGE_ACCOUNT_KEY",
    "AZURE_STORAGE_CONTAINER_NAME",
    "COSMOS_DB_ENDPOINT",
    "COSMOS_DB_KEY",
    "COSMOS_DB_NAME",
    "COSMOS_DB_CONTAINER_NAME",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_KEY",
    "AZURE_OPENAI_DEPLOYMENT_NAME",
    "AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS_NAME",
    "AZURE_OPENAI_API_VERSION",
]


class ConfigError(RuntimeError):
    pass


def _load() -> dict:
    missing = [v for v in REQUIRED_VARS if not os.environ.get(v, "").strip()]
    if missing:
        raise ConfigError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    values = {v: os.environ[v].strip() for v in REQUIRED_VARS}

    # Validate URLs parse with hostnames — mispasted secrets fail loudly at boot.
    for url_var in ("AZURE_OPENAI_ENDPOINT", "COSMOS_DB_ENDPOINT"):
        parsed = urlparse(values[url_var])
        if not parsed.scheme or not parsed.hostname:
            raise ConfigError(
                f"Environment variable {url_var} is malformed: "
                f"expected a URL with scheme and hostname, got {values[url_var]!r}"
            )

    return values


_cfg = _load()

AZURE_STORAGE_ACCOUNT_NAME = _cfg["AZURE_STORAGE_ACCOUNT_NAME"]
AZURE_STORAGE_ACCOUNT_KEY = _cfg["AZURE_STORAGE_ACCOUNT_KEY"]
AZURE_STORAGE_CONTAINER_NAME = _cfg["AZURE_STORAGE_CONTAINER_NAME"]

COSMOS_DB_ENDPOINT = _cfg["COSMOS_DB_ENDPOINT"]
COSMOS_DB_KEY = _cfg["COSMOS_DB_KEY"]
COSMOS_DB_NAME = _cfg["COSMOS_DB_NAME"]
COSMOS_DB_CONTAINER_NAME = _cfg["COSMOS_DB_CONTAINER_NAME"]

AZURE_OPENAI_ENDPOINT = _cfg["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_KEY = _cfg["AZURE_OPENAI_KEY"]
AZURE_OPENAI_DEPLOYMENT_NAME = _cfg["AZURE_OPENAI_DEPLOYMENT_NAME"]
AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS_NAME = _cfg["AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS_NAME"]
AZURE_OPENAI_API_VERSION = _cfg["AZURE_OPENAI_API_VERSION"]

# Tunables (with safe defaults).
EMBEDDING_BATCH_SIZE = int(os.environ.get("EMBEDDING_BATCH_SIZE", "16"))
CHUNK_SIZE_CHARS = int(os.environ.get("CHUNK_SIZE_CHARS", "1200"))
CHUNK_OVERLAP_CHARS = int(os.environ.get("CHUNK_OVERLAP_CHARS", "150"))
TOP_K = int(os.environ.get("TOP_K", "5"))
