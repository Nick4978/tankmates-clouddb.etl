# etl/transform.py
from __future__ import annotations
import csv, os
from typing import Dict, Any, Iterable, Mapping, Optional
from datetime import datetime, timezone
import requests

LOG_PATH = os.environ.get("ETL_LOG_CSV", "etl_log.csv")
LOG_SAS_URL = os.environ.get("ETL_LOG_SAS_URL") 

# ------------------- Helpers -------------------

def _to_bool(v) -> Optional[bool]:
    if v is None: return None
    if isinstance(v, bool): return v
    try:
        iv = int(v)
        if iv in (0, 1): return bool(iv)
    except Exception:
        pass
    s = str(v).strip().lower()
    if s in {"true","t","yes","y","1"}: return True
    if s in {"false","f","no","n","0"}: return False
    return None

def _epoch_to_iso(v) -> Optional[str]:
    if v is None or v == "": return None
    try:
        x = int(v)
        dt = datetime.fromtimestamp(x/1000 if x > 10_000_000_000 else x, tz=timezone.utc)
        return dt.isoformat()
    except Exception:
        return None

# ------------------- CSV Logger -------------------

class CsvLogger:
    def __init__(self, path: str):
        self.path = path
        self._fh = open(path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._fh, fieldnames=["table","id","status","warnings"])
        self._writer.writeheader()
        self.stats = {"processed":0,"errors":0,"warnings":0}
        self.table_stats: Dict[str, Dict[str,int]] = {}  # {table:{processed,ok,warn,error}}

    def _ensure_table(self, table: str):
        self.table_stats.setdefault(table, {"processed":0,"ok":0,"warn":0,"error":0})

    def log(self, table: str, id_: str, status: str, warnings: list[str]):
        self._ensure_table(table)
        self._writer.writerow({
            "table": table,
            "id": id_,
            "status": status,
            "warnings": "; ".join(warnings) if warnings else ""
        })
        self.stats["processed"] += 1
        self.table_stats[table]["processed"] += 1
        if status == "error":
            self.stats["errors"] += 1
            self.table_stats[table]["error"] += 1
        elif status == "warn":
            self.stats["warnings"] += 1
            self.table_stats[table]["warn"] += 1
        else:
            self.table_stats[table]["ok"] += 1

    def close(self):
        self._fh.close()
        # Print per-table summary
        print("\n============ CSV LOG SUMMARY (by table) ============\n")
        for tbl, s in sorted(self.table_stats.items()):
            print(f"{tbl:24} | processed={s['processed']:5d}  ok={s['ok']:5d}  warn={s['warn']:4d}  error={s['error']:4d}")
        print("\nTOTALS")
        print(f"  processed={self.stats['processed']}  warnings={self.stats['warnings']}  errors={self.stats['errors']}")
        print(f"\nDetailed CSV log written to {self.path}\n")

        if LOG_SAS_URL:
            try:
                with open(self.path, "rb") as f:
                    r = requests.put(
                        LOG_SAS_URL,
                        data=f,
                        headers={"x-ms-blob-type": "BlockBlob", "Content-Type": "text/csv"}
                    )
                r.raise_for_status()
                print(f"Uploaded ETL log to Storage via SAS: {LOG_SAS_URL.split('?')[0]}")
            except Exception as e:
                print(f"WARNING: failed to upload ETL CSV log via SAS: {e}")

LOGGER = CsvLogger(LOG_PATH)

def log_invalid(table: str, id_value: Optional[str], reason: str):
    """Use this from run.py when you skip a row (e.g., missing Id/PK)."""
    LOGGER.log(table, id_value or "<none>", "error", [reason])

# ------------------- Transform -------------------

def transform_item(
    table: str,
    item: Dict[str, Any],
    cfg: Mapping[str, Any],
    tenant_field: str,
    tenant_id: Optional[str]
) -> Dict[str, Any]:
    warnings: list[str] = []

    id_field = cfg.get("idField","Id")
    # ensure id string
    if id_field in item and item[id_field] is not None:
        if not isinstance(item[id_field], str):
            item[id_field] = str(item[id_field])
    else:
        warnings.append(f"missing id field {id_field}")

    # tenant
    if tenant_field not in item or not str(item.get(tenant_field, "")).strip():
        item[tenant_field] = tenant_id or "00000000-0000-0000-0000-000000000000"
        warnings.append("tenantId injected")

    # booleans
    for f in cfg.get("boolFields",[]):
        if f in item:
            b = _to_bool(item[f])
            if b is not None:
                item[f] = b
            else:
                warnings.append(f"bool parse fail {f}={item[f]}")

    # dates
    for f in cfg.get("dateFields",[]):
        if f in item:
            iso = _epoch_to_iso(item[f])
            if iso:
                item[f+"Iso"] = iso
            else:
                warnings.append(f"date parse fail {f}={item[f]}")

    # status: ok if no warnings, else warn (errors are logged when skipping in run.py)
    status = "ok" if not warnings else "warn"
    LOGGER.log(table, item.get(id_field,"<none>"), status, warnings)
    return item

def transform_batch(table: str, batch: list[Dict[str,Any]], cfg_for_table: Mapping[str,Any], tenant_field: str, tenant_id: Optional[str]) -> list[Dict[str,Any]]:
    return [transform_item(table, it, cfg_for_table, tenant_field, tenant_id) for it in batch]

def close_logger():
    LOGGER.close()
