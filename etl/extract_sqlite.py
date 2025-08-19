import sqlite3
from typing import Iterator, Dict, Any, List

def stream_rows(db_path: str, table: str, batch_size: int = 500) -> Iterator[List[Dict[str, Any]]]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(f"SELECT * FROM {table}")
    while True:
        rows = cur.fetchmany(batch_size)
        if not rows:
            break
        yield [dict(r) for r in rows]
    cur.close()
    con.close()
