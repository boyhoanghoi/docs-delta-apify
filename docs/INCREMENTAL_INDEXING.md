# Incremental index updates without nested page parsing

DocsDelta now exports **CHUNK_OPERATIONS** and **chunk-operations.ndjson** in
addition to the existing page dataset, `CHANGES`, `RAG_CHUNKS` and `SNAPSHOT`.
The feed is for search/RAG systems that need explicit insert/update/delete work.
It does not create embeddings or connect to your vector database.

## Operation contract

Each operation has `operation`, `id`, `sourceUrl`, `pageStatus`,
`pageContentHash` and `observedAt`.

| Operation | Additional fields | Action in your index |
| --- | --- | --- |
| `REMOVE` | None | Delete this ID only within its source page and your corpus namespace. Deleting a missing ID should succeed. |
| `UPSERT` | `text`, `heading`, `index`, `contentHash`, `isNewChunk` | Insert or replace the chunk and its current page metadata using the ID as a stable key. |

Only saved `NEW` and `UPDATED` pages generate operations. A saved `UNCHANGED`
page generates zero operations, although the page check is billed under default
settings. Set `changedOnly: true` to suppress unchanged rows and paid page events.

For each changed page, explicit `REMOVE` operations come first, followed by
`UPSERT` operations for **all** current chunks in document order. Retained chunks
also receive an upsert: inserting an earlier section can move their `index`, and
the parent page's content hash changes. `isNewChunk: false` means the ID existed
in the supplied baseline. Reuse an existing embedding only when your index also
has that chunk and its matching `contentHash`; metadata may still need updating.

The same operation batch can be replayed safely when your deletes ignore missing
IDs and your upserts replace by ID. Apply an entire batch before promoting its
new snapshot. If index writes fail halfway through, keep the previous baseline
and replay; never assume an exported snapshot means the index was updated.

There is no `REMOVE_PAGE` operation. A 404, absent sitemap entry, blocked page,
partial run or exhausted budget cannot prove deletion. A chunk is removed only
after the same page was completely fetched, extracted and successfully saved.
Unpaid/unsaved pages generate neither operations nor baseline advancement.

## Apify workflow

1. Read your stored baseline and start DocsDelta with that object in
   `previousSnapshot`, your URLs and `changedOnly: true`.
2. Wait for the run to succeed. Download `CHUNK_OPERATIONS` or its NDJSON version,
   plus `SNAPSHOT`, `SUMMARY` and `DIAGNOSTICS` from that run's default key-value store.
3. Apply the operations to your corpus. Do not clear a corpus when the feed is empty.
4. Once all index writes are confirmed, store the new `SNAPSHOT` for the next run.
5. Investigate skipped sources in diagnostics; their previous baseline remains.

Calling applications still supply state explicitly. A fixed Apify schedule alone
does not load the previous snapshot, and no shared named store is created.
The Actor price remains $0.003 per successfully saved page; operation records and
nested chunks do not add custom events. Check the current Store pricing for terms.

## Local recurring exports

For a folder of local exports, create/update a separate reusable checkpoint:

```bash
docsdelta --input examples/changed-only.json --output output --snapshot-file state/docs-snapshot.json
```

Run that same command again to load the previous checkpoint. A missing checkpoint
starts with an empty baseline; an existing invalid checkpoint fails before any
network requests. All output files must finish before the checkpoint is replaced.
Each file replacement is atomic; the folder as a whole is not a transaction.
A failed export keeps the previous checkpoint, but earlier result files may
already contain the new batch. Inspect and retry from the last confirmed baseline.
Keep one process per checkpoint file; concurrent runs are not coordinated.

For an external index, prefer the read-only baseline flag so you choose when to
promote state after indexing:

```bash
# Bootstrap the first batch without a previous baseline.
docsdelta --input examples/changed-only.json --output output/run-1
# Apply run-1/chunk-operations.ndjson to your index, then retain run-1/snapshot.json.
docsdelta --input examples/changed-only.json --output output/run-2 --previous-snapshot output/run-1/snapshot.json
```

`--previous-snapshot` requires an existing file. `--snapshot-file` both loads and
updates its file. The flags are mutually exclusive; a nonempty inline
`previousSnapshot` cannot be combined with either. Snapshot JSON files are bounded
to 5 MiB and validated exactly like Actor baselines. The local input file is
bounded to 6 MiB. Exports include `chunk-operations.json`,
`chunk-operations.ndjson`, `rag-chunks.json`, page results, diagnostics, summary
and compact `snapshot.json`.

Changing selectors or chunk size can produce chunk removals/upserts even when
the original page has not changed. Keep extraction settings and input URLs
consistent, or treat configuration changes as an intentional re-index.
