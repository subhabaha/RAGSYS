"""Embeddings + chat helpers.

The Azure OpenAI resource is shared: batch requests, respect HTTP 429 with
bounded exponential backoff, and surface failure rather than retrying forever.
"""
from __future__ import annotations

import logging
import random
import time
from typing import List

from openai import APIStatusError, RateLimitError

from . import config
from .azure_clients import get_openai_client

log = logging.getLogger(__name__)

MAX_RETRIES = 6
BASE_DELAY = 2.0
MAX_DELAY = 60.0


def _sleep_backoff(attempt: int, retry_after: float | None) -> None:
    if retry_after is not None:
        delay = min(retry_after, MAX_DELAY)
    else:
        delay = min(MAX_DELAY, BASE_DELAY * (2 ** attempt)) * (0.5 + random.random())
    log.warning("Rate limited by Azure OpenAI; sleeping %.1fs (attempt %d)", delay, attempt + 1)
    time.sleep(delay)


def _retry_after_seconds(err: Exception) -> float | None:
    resp = getattr(err, "response", None)
    if resp is None:
        return None
    val = resp.headers.get("retry-after") if hasattr(resp, "headers") else None
    try:
        return float(val) if val else None
    except (TypeError, ValueError):
        return None


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Return one embedding per input text, batching and handling 429."""
    if not texts:
        return []
    client = get_openai_client()
    out: List[List[float]] = []
    batch_size = max(1, config.EMBEDDING_BATCH_SIZE)
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        attempt = 0
        while True:
            try:
                resp = client.embeddings.create(
                    model=config.AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS_NAME,
                    input=batch,
                )
                out.extend([d.embedding for d in resp.data])
                break
            except RateLimitError as e:
                if attempt >= MAX_RETRIES:
                    raise
                _sleep_backoff(attempt, _retry_after_seconds(e))
                attempt += 1
            except APIStatusError as e:
                if e.status_code == 429 and attempt < MAX_RETRIES:
                    _sleep_backoff(attempt, _retry_after_seconds(e))
                    attempt += 1
                    continue
                raise
    return out


def embed_query(text: str) -> List[float]:
    return embed_texts([text])[0]


def chat_answer(question: str, context_blocks: List[str]) -> str:
    client = get_openai_client()
    context = "\n\n---\n\n".join(context_blocks)
    system = (
        "You are a helpful assistant answering questions strictly from the "
        "provided document excerpts. If the answer is not present, say you "
        "don't know. Cite excerpts implicitly by using their content."
    )
    user = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    attempt = 0
    while True:
        try:
            resp = client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
            )
            return resp.choices[0].message.content or ""
        except RateLimitError as e:
            if attempt >= MAX_RETRIES:
                raise
            _sleep_backoff(attempt, _retry_after_seconds(e))
            attempt += 1
        except APIStatusError as e:
            if e.status_code == 429 and attempt < MAX_RETRIES:
                _sleep_backoff(attempt, _retry_after_seconds(e))
                attempt += 1
                continue
            raise
