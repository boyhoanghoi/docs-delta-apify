# Incremental indexing upgrade — 16 October 2026

This note describes the incremental indexing upgrade. Deployment and public
release verification are recorded separately in `LAUNCH_STATUS.md`.

## Changes

- Added `CHUNK_OPERATIONS` JSON and `chunk-operations.ndjson` exports with
  explicit REMOVE/UPSERT operations from saved changed pages only. Retained
  chunks refresh metadata and positions; `isNewChunk` supports embedding reuse.
- Added local `--previous-snapshot FILE` and `--snapshot-file FILE` flags, bounded
  UTF-8 input, atomic file replacement and checkpoint promotion after exports.
- Local `snapshot.json` now uses the same compact JSON representation as the
  reusable snapshot byte bound, rather than adding indentation overhead.
- Corrected code-fence parsing so a shorter fence inside a longer fenced code
  block does not turn code comments into false document headings.
- Added English and Vietnamese indexing/checkpoint documentation and native
  output-schema links. No pricing or account changes.
- Reject unknown input fields and non-integer snapshot versions rather than
  silently accepting typos that can change billing behavior. Deep malformed
  local JSON inputs fail clearly before network requests.

## Verification

- **46 Python unit tests passed**, including operation replay, retained chunk
  positions, REMOVE scope, failed/404/unsaved baseline preservation, zero-budget
  empty exports, paid-limit export boundaries and atomic checkpoint failures.
- Official Apify CLI validated input, dataset and output schemas.
- Live local run with `examples/changed-only.json`: 1 NEW Python documentation
  page, 22 UPSERT operations, 0 removes. Repeated with the same checkpoint:
  1 UNCHANGED page filtered, 0 saved rows/operations, baseline preserved exactly.
  These are owner tests, not customer demand or revenue.

Recommended release smoke: run `examples/first-run.json` with a small cost cap,
check dataset/event counts and CHUNK_OPERATIONS, then pass its SNAPSHOT back with
changedOnly=true and verify zero operations when sources remain unchanged.

No page-deletion inference, automatic cloud state, JavaScript browser extraction,
embedding service or vector database integration is added. The calling workflow
still passes cloud snapshots explicitly and confirms index writes before
promoting state. Per-file replacement is atomic; the entire local output folder
is not a transaction and concurrent writers are not coordinated.
