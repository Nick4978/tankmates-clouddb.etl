from __future__ import annotations
import os
import sys
import json
import asyncio
from typing import Dict, Any

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient

from extract_sqlite import stream_rows
from transform import transform_batch, close_logger, log_invalid, LOG_PATH
from load_cosmos import CosmosLoader

# --------- Environment (provided by Container Apps Job) ----------
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")          # used for RBAC path
COSMOS_CONNSTR  = os.getenv("COSMOS_CONNSTR")           # preferred if present

ST_ACC     = os.getenv("STORAGE_ACCOUNT")
ST_CONT    = os.getenv("STORAGE_CONTAINER", "ingest")
ST_DB_BLOB = os.getenv("SQLITE_BLOB_NAME", "tankmates.db")
ST_LOG_BLOB= os.getenv("ETL_LOG_BLOB_NAME", "etl_log.csv")

CONFIG_PATH = os.getenv("CONFIG_PATH", "/workspace/etl/config.example.json")


# --------------------- Storage helpers (AAD) ---------------------
def _blob_client(account: str, container: str, blob: str) -> BlobClient:
    cred = DefaultAzureCredential()
    url = f"https://{account}.blob.core.windows.net/{container}/{blob}"
    return BlobClient.from_blob_url(url, credential=cred)

def _download_sqlite_with_mi(target_path: str):
    bc = _blob_client(ST_ACC, ST_CONT, ST_DB_BLOB)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "wb") as f:
        stream = bc.download_blob(max_concurrency=4)
        f.write(stream.readall())

def _upload_log_with_mi(log_path: str):
    bc = _blob_client(ST_ACC, ST_CONT, ST_LOG_BLOB)
    with open(log_path, "rb") as f:
        bc.upload_blob(f, overwrite=True, content_type="text/csv")


# ----------------------- Metrics utilities -----------------------
def _new_table_metrics() -> Dict[str, Any]:
    return {
        "rows_read": 0,
        "rows_transformed": 0,
        "missing_id": 0,
        "missing_pk": 0,
        "ok_upserts": 0,
        "err_upserts": 0,
        "bool_normalized": 0,
        "bool_parse_failed": 0,
        "dates_iso_added": 0,
        "errors": []
    }

def _validate_item(it: Dict[str, Any], id_field: str, pk_field: str, tm: Dict[str, Any]):
    if not str(it.get(id_field, "")).strip():
        tm["missing_id"] += 1
    if not str(it.get(pk_field, "")).strip():
        tm["missing_pk"] += 1

    stats = it.pop("__xform_stats__", None)
    if stats:
        tm["bool_normalized"]   += stats.get("bool_normalized", 0)
        tm["bool_parse_failed"] += stats.get("bool_parse_failed", 0)
        tm["dates_iso_added"]   += stats.get("dates_iso_added", 0)


# ----------------------------- Main ------------------------------
async def main():
    # Basic env validation
    for k, v in {
        "STORAGE_ACCOUNT": ST_ACC,
        "STORAGE_CONTAINER": ST_CONT,
        "SQLITE_BLOB_NAME": ST_DB_BLOB,
    }.items():
        if not v:
            print(f"ERROR: missing env var {k}", file=sys.stderr)
            sys.exit(2)

    # Download SQLite
    db_path = "/workspace/data.db"
    print(f"Downloading SQLite blob '{ST_DB_BLOB}' from '{ST_ACC}/{ST_CONT}'...")
    _download_sqlite_with_mi(db_path)

    # Load ETL config
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg: Dict[str, Any] = json.load(f)

    database       = cfg["database"]
    containers_cfg = cfg["containers"]  # dict: table -> config
    batch_size     = int(cfg.get("batchSize", 500))
    concurrency    = int(cfg.get("concurrency", 4))
    tenant_id      = cfg.get("tenantId")
    tenant_field   = "tenantId"

    # Create Cosmos loader (prefer connection string if supplied)
    if COSMOS_CONNSTR and COSMOS_CONNSTR.strip():
        print("Using Cosmos connection string (key-based) for this run.")
        loader_ctx = CosmosLoader.from_connection_string(COSMOS_CONNSTR, database)
    else:
        if not COSMOS_ENDPOINT:
            print("ERROR: COSMOS_ENDPOINT is required when COSMOS_CONNSTR is not provided.", file=sys.stderr)
            sys.exit(3)
        print("Using Managed Identity / RBAC for Cosmos.")
        loader_ctx = CosmosLoader(COSMOS_ENDPOINT, database)

    summary: Dict[str, Dict[str, Any]] = {}

    async with loader_ctx as loader:
        for table, meta in containers_cfg.items():
            container_name = table
            table_metrics = _new_table_metrics()
            id_field = meta.get("idField", "Id")
            pk_field = meta.get("pkField", tenant_field)

            print(f"\n=== Processing {table} -> {container_name} ===")
            for batch in stream_rows(db_path, table, batch_size):
                table_metrics["rows_read"] += len(batch)

                cfg_fields = {
                    "boolFields": meta.get("boolFields"),
                    "dateFields": meta.get("dateFields"),
                    "idField": id_field,
                    "pkField": pk_field
                }

                # Transform
                batch = transform_batch(table, batch, cfg_fields, tenant_field, tenant_id)

                # Validate, filter invalid
                valid_batch = []
                for it in batch:
                    _validate_item(it, id_field, pk_field, table_metrics)
                    if not str(it.get(id_field, "")).strip() or not str(it.get(pk_field, "")).strip():
                        ident = str(it.get(id_field, "<no-id>"))
                        table_metrics["errors"].append(f"{table}:{ident}:invalid:missing-id-or-pk")
                        log_invalid(table, ident, "missing-id-or-pk")
                        continue
                    valid_batch.append(it)

                table_metrics["rows_transformed"] += len(valid_batch)
                if not valid_batch:
                    continue

                # Load
                ok, err, errs = await loader.upsert_items(container_name, valid_batch, concurrency=concurrency)
                table_metrics["ok_upserts"]  += ok
                table_metrics["err_upserts"] += err
                if errs:
                    table_metrics["errors"].extend(errs[:20])

            summary[table] = table_metrics

    # Print summary
    print("\n================ ETL SUMMARY ================\n")
    total_read = total_ok = total_err = total_missing_id = total_missing_pk = 0
    for table, m in summary.items():
        total_read       += m["rows_read"]
        total_ok         += m["ok_upserts"]
        total_err        += m["err_upserts"]
        total_missing_id += m["missing_id"]
        total_missing_pk += m["missing_pk"]
        print(f"{table:24} | read={m['rows_read']:5d}  xform={m['rows_transformed']:5d}  "
              f"ok={m['ok_upserts']:5d}  err={m['err_upserts']:3d}  "
              f"missId={m['missing_id']:3d}  missPK={m['missing_pk']:3d}  "
              f"bool+={m['bool_normalized']:3d}  bool?={m['bool_parse_failed']:3d}  date+={m['dates_iso_added']:3d}")
        if m["errors"]:
            print(f"  └─ errors (sample):")
            for e in m["errors"][:5]:
                print(f"     - {e}")

    print("\nTOTALS")
    print(f"  rows_read={total_read}  ok={total_ok}  err={total_err}  missing_id={total_missing_id}  missing_pk={total_missing_pk}")
    print("\n============================================\n")

    # Close CSV logger (implemented in transform.py)
    close_logger()

    # Upload the CSV log to Storage (AAD)
    try:
        _upload_log_with_mi(LOG_PATH)
        print(f"Uploaded CSV log to blob '{ST_LOG_BLOB}' in '{ST_ACC}/{ST_CONT}'.")
    except Exception as e:
        print(f"WARNING: failed to upload CSV log to Storage: {e}")


if __name__ == "__main__":
    asyncio.run(main())