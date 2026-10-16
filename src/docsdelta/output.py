import csv
import io
import json


def pages_csv(rows):
    fields = ["url", "finalUrl", "title", "canonicalUrl", "status", "contentHash", "observedAt", "chunkCount", "addedChunkCount", "removedChunkCount", "diff"]
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        values = {key: row.get(key, "") for key in fields}
        values.update(chunkCount=len(row["chunks"]), addedChunkCount=len(row["addedChunkIds"]), removedChunkCount=len(row["removedChunkIds"]))
        for key, value in values.items():
            if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                values[key] = "'" + value
        writer.writerow(values)
    return "\ufeff" + out.getvalue()


def rag_chunks(rows):
    return [{**chunk, "pageStatus": row["status"], "pageContentHash": row["contentHash"]} for row in rows for chunk in row["chunks"]]


def chunk_operations(rows):
    """Replayable per-page index operations from accepted changed rows only.

    Refresh all current chunk metadata, including the index of retained chunks.
    An absent or unsuccessfully fetched page is never a deletion signal.
    """
    operations = []
    for row in rows:
        if row["status"] not in {"NEW", "UPDATED"}:
            continue
        metadata = {"sourceUrl": row["url"], "pageStatus": row["status"],
            "pageContentHash": row["contentHash"], "observedAt": row["observedAt"]}
        for chunk_id in row["removedChunkIds"]:
            operations.append({"operation": "REMOVE", "id": chunk_id, **metadata})
        added = set(row["addedChunkIds"])
        for chunk in row["chunks"]:
            operations.append({**chunk, **metadata, "operation": "UPSERT", "isNewChunk": chunk["id"] in added})
    return operations


def ndjson(rows):
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
