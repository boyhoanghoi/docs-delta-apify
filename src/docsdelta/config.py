from __future__ import annotations
from dataclasses import dataclass, field
import hashlib
import json
import re
import soupsieve

DEFAULT_URLS = ["https://docs.python.org/3/tutorial/datastructures.html", "https://docs.djangoproject.com/en/stable/intro/overview/"]


@dataclass(frozen=True)
class RunConfig:
    urls: list[str] = field(default_factory=lambda: list(DEFAULT_URLS))
    sitemap_urls: list[str] = field(default_factory=list)
    max_pages: int = 5
    follow_links: bool = False
    content_css_selector: str | None = None
    exclude_css_selectors: tuple[str, ...] = ()
    min_text_length: int = 40
    max_text_chars: int = 120000
    chunk_size: int = 1800
    max_chunks: int = 200
    include_unchanged: bool = True
    changed_only: bool = False
    previous_snapshot: dict = field(default_factory=lambda: {"version": 1, "pages": {}})
    respect_robots: bool = True
    timeout_seconds: int = 30
    min_delay_seconds: float = 0.5
    concurrency: int = 1

    @classmethod
    def from_dict(cls, data: dict) -> "RunConfig":
        if not isinstance(data, dict):
            raise ValueError("Input must be a JSON object.")
        def integer(key, default, low, high):
            value = data.get(key, default)
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise ValueError(f"{key} must be an integer between {low} and {high}.")
            return value
        def boolean(key, default):
            value = data.get(key, default)
            if not isinstance(value, bool):
                raise ValueError(f"{key} must be a boolean.")
            return value
        def urls(key, default):
            value = data.get(key, default)
            if not isinstance(value, list) or len(value) > 1000 or any(not isinstance(v, str) for v in value):
                raise ValueError(f"{key} must be an array of at most 1000 URL strings.")
            # Import here to keep the transport/config dependency acyclic.
            from .transport import validate_url, FetchError
            try:
                return list(dict.fromkeys(validate_url(v) for v in value))
            except FetchError as exc:
                raise ValueError(f"{key}: {exc}") from None
        seeds = urls("urls", [] if data.get("sitemapUrls") else DEFAULT_URLS)
        sitemaps = urls("sitemapUrls", [])
        if not seeds and not sitemaps:
            raise ValueError("Provide urls or sitemapUrls.")
        selector = data.get("contentCssSelector") or None
        excludes = data.get("excludeCssSelectors", [])
        if selector is not None and not isinstance(selector, str):
            raise ValueError("contentCssSelector must be a CSS selector string.")
        if not isinstance(excludes, list) or len(excludes) > 30 or any(not isinstance(v, str) for v in excludes):
            raise ValueError("excludeCssSelectors must be an array of up to 30 selectors.")
        for value in ([selector] if selector else []) + excludes:
            if len(value) > 500:
                raise ValueError("CSS selector exceeds 500 characters.")
            try:
                soupsieve.compile(value)
            except Exception as exc:
                raise ValueError(f"Invalid CSS selector: {value!r}.") from exc
        return cls(urls=seeds, sitemap_urls=sitemaps, max_pages=integer("maxPages", 5, 1, 500),
            follow_links=boolean("followLinks", False), content_css_selector=selector,
            exclude_css_selectors=tuple(excludes), min_text_length=integer("minTextLength", 40, 40, 10000),
            max_text_chars=integer("maxTextChars", 120000, 1000, 120000),
            chunk_size=integer("chunkSize", 1800, 200, 8000), max_chunks=integer("maxChunksPerPage", 200, 1, 200),
            include_unchanged=boolean("includeUnchanged", True), changed_only=boolean("changedOnly", False),
            previous_snapshot=validate_snapshot(data.get("previousSnapshot")),
            timeout_seconds=integer("timeoutSeconds", 30, 5, 60))


def validate_snapshot(value: dict | None) -> dict:
    if value is None:
        return {"version": 1, "pages": {}}
    if not isinstance(value, dict) or value.get("version") != 1 or not isinstance(value.get("pages"), dict):
        raise ValueError("previousSnapshot must be a version:1 object with a pages mapping.")
    if len(value["pages"]) > 2000 or len(json.dumps(value, ensure_ascii=False).encode("utf-8")) > 5 * 1024 * 1024:
        raise ValueError("previousSnapshot exceeds the 2000-page / 5 MiB bound.")
    from .transport import validate_url, FetchError
    clean = {}
    for url, page in value["pages"].items():
        try:
            normalized = validate_url(url)
        except FetchError as exc:
            raise ValueError(f"Invalid snapshot URL: {exc}") from None
        if normalized != url or not isinstance(page, dict):
            raise ValueError("Snapshot keys must be normalized HTTP(S) URLs and values must be objects.")
        markdown = page.get("markdown")
        content_hash = page.get("contentHash")
        chunks = page.get("chunks")
        if not isinstance(markdown, str) or len(markdown) > 120000:
            raise ValueError("Snapshot pages require markdown of at most 120000 characters.")
        if not isinstance(content_hash, str) or hashlib.sha256(markdown.encode()).hexdigest() != content_hash:
            raise ValueError("Snapshot contentHash must match the UTF-8 markdown SHA-256.")
        if not isinstance(chunks, list) or len(chunks) > 200:
            raise ValueError("Snapshot chunks must be an array of at most 200 objects.")
        ids = []
        for chunk in chunks:
            if not isinstance(chunk, dict) or not isinstance(chunk.get("id"), str) or not re.fullmatch(r"[a-f0-9]{24}", chunk["id"]):
                raise ValueError("Snapshot chunk IDs must be 24 lowercase hex characters.")
            if not isinstance(chunk.get("text"), str) or len(chunk["text"]) > 8000:
                raise ValueError("Snapshot chunk text must be bounded to 8000 characters.")
            if chunk.get("sourceUrl") != url:
                raise ValueError("Snapshot chunk sourceUrl must match its page key.")
            if chunk.get("contentHash") != hashlib.sha256(chunk["text"].encode()).hexdigest():
                raise ValueError("Snapshot chunk contentHash does not match its text.")
            ids.append(chunk["id"])
        if len(ids) != len(set(ids)):
            raise ValueError("Snapshot chunk IDs must be unique within each page.")
        clean[url] = json.loads(json.dumps(page))
    return {"version": 1, "pages": clean}
