"""Azure client factories.

All Azure SDKs used here are synchronous. Callers must NOT invoke these on the
event loop directly for long-running operations — use `asyncio.to_thread` or a
plain `def` background task (Starlette runs those in a threadpool).
"""
from __future__ import annotations

import logging

from azure.core.exceptions import ResourceExistsError
from azure.cosmos import CosmosClient, PartitionKey
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI

from . import config

log = logging.getLogger(__name__)


def _blob_service() -> BlobServiceClient:
    account_url = f"https://{config.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
    return BlobServiceClient(
        account_url=account_url, credential=config.AZURE_STORAGE_ACCOUNT_KEY
    )


def get_blob_container():
    """Return the blob container client, creating the container if missing."""
    svc = _blob_service()
    container = svc.get_container_client(config.AZURE_STORAGE_CONTAINER_NAME)
    try:
        container.create_container()
        log.info("Created blob container %s", config.AZURE_STORAGE_CONTAINER_NAME)
    except ResourceExistsError:
        pass
    return container


def get_cosmos_container():
    """Return the Cosmos container client, creating DB and container if missing."""
    client = CosmosClient(config.COSMOS_DB_ENDPOINT, credential=config.COSMOS_DB_KEY)
    db = client.create_database_if_not_exists(id=config.COSMOS_DB_NAME)
    container = db.create_container_if_not_exists(
        id=config.COSMOS_DB_CONTAINER_NAME,
        partition_key=PartitionKey(path="/id"),
    )
    return container


def get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=config.AZURE_OPENAI_KEY,
        api_version=config.AZURE_OPENAI_API_VERSION,
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
    )
