"""Bounded crawl, explicit page comparison, and conservative snapshot handoff."""
from __future__ import annotations
import copy
import difflib
import json
from collections import Counter, deque
from datetime import datetime, timezone
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
from .config import RunConfig
from .extract import extract_document
from .transport import FetchError, SafeHttpClient, validate_url, same_site

MAX_SNAPSHOT_BYTES = 5 * 1024 * 1024
MAX_RUN_CHARS = 4_000_000


def compare_document(document: dict, previous: dict | None) -> dict:
    before = set(chunk["id"] for chunk in previous.get("chunks", [])) if previous else set()
    after = set(chunk["id"] for chunk in document["chunks"])
    status = "NEW" if previous is None else "UNCHANGED" if previous["contentHash"] == document["contentHash"] and before == after else "UPDATED"
    diff = []
    shortened_line = False
    if status == "UPDATED":
        # Split normalized Markdown into physical lines, bound both diff work and output.
        old = previous["markdown"].splitlines()[:4000]
        new = document["markdown"].splitlines()[:4000]
        iterator = difflib.unified_diff(old, new, fromfile="previous", tofile="current", n=2, lineterm="")
        for line in iterator:
            if len(line) > 1000:
                shortened_line = True
                line = line[:480] + " ... [line shortened] ... " + line[-480:]
            diff.append(line)
            if len(diff) >= 200:
                break
    return {"status": status, "diff": "\n".join(diff),
        "diffTruncated": status == "UPDATED" and (shortened_line or len(diff) >= 200 or len(previous["markdown"].splitlines()) > 4000 or len(document["markdown"].splitlines()) > 4000),
        "addedChunkIds": sorted(after - before), "removedChunkIds": sorted(before - after)}


def snapshot_entry(document: dict) -> dict:
    return {"contentHash": document["contentHash"], "markdown": document["markdown"], "chunks": document["chunks"]}


async def discover_sitemaps(config: RunConfig, client, diagnostics: list) -> list[str]:
    pending = deque((url, 0, url) for url in config.sitemap_urls)
    seen, pages = set(), []
    while pending and len(seen) < 10 and len(pages) < 2000:
        url, depth, scope = pending.popleft()
        if url in seen:
            continue
        seen.add(url)
        try:
            response = await client.fetch(url, scope_url=scope)
            if "<!DOCTYPE" in response.text.upper() or "<!ENTITY" in response.text.upper():
                raise FetchError("invalid_sitemap", "DTD/entity declarations are not supported.")
            root = ET.fromstring(response.text)
            kind = root.tag.rsplit("}", 1)[-1]
            if kind not in {"urlset", "sitemapindex"}:
                raise FetchError("invalid_sitemap", "Expected urlset or sitemapindex XML.")
            for entry in root:
                location = next((node.text.strip() for node in entry if node.tag.rsplit("}", 1)[-1] == "loc" and node.text), None)
                if not location:
                    continue
                try:
                    target = validate_url(location)
                except FetchError:
                    continue
                if not same_site(scope, target):
                    continue
                if kind == "sitemapindex":
                    if depth < 2 and len(pending) < 30:
                        pending.append((target, depth + 1, scope))
                elif len(pages) < 2000:
                    pages.append(target)
        except (FetchError, ET.ParseError) as exc:
            diagnostics.append({"url": url, "status": getattr(exc, "status", "invalid_sitemap"), "message": str(exc), "phase": "sitemap"})
    if pending or len(pages) >= 2000:
        diagnostics.append({"status": "sitemap_limit", "message": "Sitemap discovery reached a bounded file/depth/entry limit.", "phase": "sitemap"})
    return list(dict.fromkeys(pages))


async def run_pipeline(config: RunConfig, on_result=None, *, client_factory=SafeHttpClient) -> dict:
    snapshot = copy.deepcopy(config.previous_snapshot)
    snapshot_bytes = len(json.dumps(snapshot, ensure_ascii=False).encode("utf-8"))
    results, diagnostics = [], []
    successful_checks = 0
    unchanged_filtered = 0
    attempted = 0
    stopped = False
    run_chars = 0
    async with client_factory(config) as client:
        discovered = await discover_sitemaps(config, client, diagnostics)
        queue = deque(dict.fromkeys(config.urls + discovered))
        seen = set()
        final_seen = set()
        scopes = config.urls + config.sitemap_urls
        while queue and attempted < config.max_pages:
            url = queue.popleft()
            if url in seen:
                continue
            seen.add(url)
            attempted += 1
            try:
                page = await client.fetch(url, scope_url=url)
                final_url = validate_url(page.url)
                if final_url in final_seen:
                    diagnostics.append({"url": url, "status": "duplicate_redirect", "message": "Final URL already processed; no extra result or charge."})
                    continue
                if not any(value in page.content_type for value in ("text/html", "application/xhtml+xml")):
                    raise FetchError("unsupported_content", "Only HTML document pages are converted; use sitemapUrls for XML.")
                document = extract_document(page.text, url, config, base_url=final_url)
                if document.get("skipReason"):
                    diagnostics.append({"url": url, "status": document["skipReason"], "message": "Page skipped without charge; prior snapshot is preserved."})
                    continue
                if run_chars + len(document["markdown"]) > MAX_RUN_CHARS:
                    diagnostics.append({"url": url, "status": "run_content_limit", "message": "Cumulative content limit reached; current/prior baseline was not replaced."})
                    stopped = True
                    break
                if config.follow_links:
                    for candidate in document["links"]:
                        if len(queue) >= 2000:
                            break
                        try:
                            target = validate_url(candidate)
                        except FetchError:
                            continue
                        if target not in seen and same_site(url, target) and not urlsplit(target).path.lower().endswith((".pdf", ".zip", ".png", ".jpg", ".gif", ".svg")):
                            queue.append(target)
                previous = snapshot["pages"].get(url)
                comparison = compare_document(document, previous)
                successful_checks += 1
                final_seen.add(final_url)
                if comparison["status"] == "UNCHANGED" and (config.changed_only or not config.include_unchanged):
                    unchanged_filtered += 1
                    continue
                entry = snapshot_entry(document)
                new_bytes = len(json.dumps(entry, ensure_ascii=False).encode("utf-8"))
                old_bytes = len(json.dumps(previous, ensure_ascii=False).encode("utf-8")) if previous else 0
                delta = new_bytes - old_bytes if previous else len(json.dumps(url, ensure_ascii=False).encode("utf-8")) + 2 + new_bytes + (2 if snapshot["pages"] else 0)
                if snapshot_bytes + delta > MAX_SNAPSHOT_BYTES or (previous is None and len(snapshot["pages"]) >= 2000):
                    diagnostics.append({"url": url, "status": "snapshot_capacity", "message": "Snapshot handoff would exceed 5 MiB/2000 pages. Split the input/baseline; page not saved or charged."})
                    stopped = True
                    break
                row = {"url": url, "finalUrl": final_url, "title": document["title"], "canonicalUrl": document["canonicalUrl"],
                    "markdown": document["markdown"], "contentHash": document["contentHash"], "chunks": document["chunks"],
                    "truncated": False, "observedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    **comparison}
                if on_result is not None and not await on_result(row):
                    stopped = True
                    break
                results.append(row)
                run_chars += len(document["markdown"])
                snapshot["pages"][url] = entry
                snapshot_bytes += delta
            except FetchError as exc:
                diagnostics.append({"url": url, "status": exc.status, "message": str(exc), "httpStatus": exc.http_status})
            except (ValueError, TypeError, RecursionError) as exc:
                diagnostics.append({"url": url, "status": "extraction_error", "message": f"Page could not be converted ({type(exc).__name__}); prior baseline preserved."})
        requests = client.requests
    return {"results": results, "diagnostics": diagnostics, "snapshot": snapshot,
        "summary": {"attemptedPages": attempted, "savedPages": len(results), "successfulChecks": successful_checks,
            "unchangedFiltered": unchanged_filtered, "statusCounts": dict(Counter(row["status"] for row in results)),
            "requests": requests, "stoppedByLimit": stopped, "queuedPagesRemaining": len(queue),
            "cannotInferDeletions": True, "pageRemovalsInferred": False,
            "snapshotPages": len(snapshot["pages"]), "snapshotMaxBytes": MAX_SNAPSHOT_BYTES}}
