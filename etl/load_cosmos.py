from __future__ import annotations
import asyncio
from typing import List, Tuple, Dict, Any, Optional

from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient, PartitionKey, exceptions as cosmos_ex

# This loader exposes an async interface while using the sync Cosmos SDK under the hood.
# We keep it simple for jobs: create DB/containers if missing, then batch upserts.

class CosmosLoader:
    def __init__(self, endpoint: str, database: str):
        """
        RBAC / Managed Identity path.
        """
        cred = DefaultAzureCredential()
        self._client = CosmosClient(url=endpoint, credential=cred)
        # Using create_database_if_not_exists keeps first run idempotent
        self._db = self._client.create_database_if_not_exists(id=database)

    @classmethod
    def from_connection_string(cls, connstr: str, database: str) -> "CosmosLoader":
        """
        Connection string (key-based) path. Useful for quick demos when RBAC roles
        are not yet available in tenant.
        """
        self = object.__new__(cls)
        self._client = CosmosClient.from_connection_string(connstr)
        self._db = self._client.create_database_if_not_exists(id=database)
        return self

    async def __aenter__(self) -> "CosmosLoader":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # CosmosClient has no async close; nothing special to do
        return False

    # -------------- Internal helpers (sync) --------------
    def _get_container_sync(self, name: str):
        # Partition key must match what you provisioned in Terraform: /tenantId
        try:
            return self._db.get_container_client(name)
        except cosmos_ex.CosmosResourceNotFoundError:
            # create if not exists (idempotent helper)
            return self._db.create_container_if_not_exists(id=name, partition_key=PartitionKey(path="/tenantId"))

    def _upsert_items_sync(self, container_name: str, items: List[Dict[str, Any]]) -> Tuple[int, int, Optional[List[str]]]:
        c = self._get_container_sync(container_name)
        ok = 0
        err = 0
        errs: List[str] = []
        for it in items:
            try:
                c.upsert_item(it)
                ok += 1
            except Exception as e:  # broad catch to continue batch
                err += 1
                # Keep a short reason string
                ident = str(it.get("id", "<no-id>"))
                errs.append(f"{container_name}:{ident}:upsert:{getattr(e, 'message', str(e))[:140]}")
        return ok, err, errs

    # -------------- Public async API --------------
    async def upsert_items(self, container_name: str, items: List[Dict[str, Any]], concurrency: int = 4) -> Tuple[int, int, Optional[List[str]]]:
        """
        Upsert a batch of items. We shard work across asyncio tasks that call the sync SDK
        via to_thread(), which is adequate for job-style workloads.
        """
        if not items:
            return 0, 0, None

        # Chunk items into small groups to parallelize safely
        chunk_size = max(1, len(items) // max(1, concurrency))
        chunks = [items[i:i+chunk_size] for i in range(0, len(items), chunk_size)]

        async def worker(batch: List[Dict[str, Any]]):
            return await asyncio.to_thread(self._upsert_items_sync, container_name, batch)

        results = await asyncio.gather(*(worker(b) for b in chunks), return_exceptions=False)

        ok = sum(r[0] for r in results)
        err = sum(r[1] for r in results)
        errs: List[str] = []
        for _, _, e3 in results:
            if e3:
                errs.extend(e3)
        return ok, err, errs[:200]  # cap