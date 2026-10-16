"""Deterministic HTML-to-Markdown conversion; no AI or browser execution."""
from __future__ import annotations
from collections import Counter
import hashlib
import re
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup, NavigableString, Tag
from .config import RunConfig


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_link(base: str, href: str) -> str | None:
    try:
        value = urljoin(base, href)
        parts = urlsplit(value)
        return value if parts.scheme in {"http", "https"} and parts.hostname else None
    except (ValueError, TypeError):
        return None


def normalize_markdown(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", "\n".join(line.rstrip() for line in value.splitlines())).strip()


def convert(node, base: str, depth: int = 0) -> str:
    if isinstance(node, NavigableString):
        return re.sub(r"\s+", " ", str(node))
    if not isinstance(node, Tag):
        return ""
    name = node.name.lower()
    if name == "pre":
        text = node.get_text().replace("\r\n", "\n").rstrip()
        runs = re.findall(r"`+", text)
        fence = "`" * max(3, max((len(v) + 1 for v in runs), default=3))
        language = ""
        code = node.find("code")
        if code:
            language = next((v.removeprefix("language-") for v in code.get("class", []) if v.startswith("language-")), "")
            language = re.sub(r"[^a-zA-Z0-9_+-]", "", language)[:30]
        return f"\n\n{fence}{language}\n{text}\n{fence}\n\n"
    if name in {"ul", "ol"}:
        lines = []
        for index, child in enumerate(node.find_all("li", recursive=False), 1):
            text = "".join(convert(v, base, depth + 1) for v in child.children).strip()
            marker = f"{index}. " if name == "ol" else "- "
            lines.append(marker + text.replace("\n", "\n  "))
        return "\n\n" + "\n".join(lines) + "\n\n"
    if name == "table":
        rows = [[re.sub(r"\s+", " ", cell.get_text(" ", strip=True)).replace("|", "\\|") for cell in row.find_all(["th", "td"])] for row in node.find_all("tr")]
        rows = [row for row in rows if row]
        if not rows:
            return ""
        width = min(max(map(len, rows)), 30)
        rows = [(row + [""] * width)[:width] for row in rows]
        rendered = ["| " + " | ".join(row) + " |" for row in rows]
        rendered.insert(1, "| " + " | ".join(["---"] * width) + " |")
        return "\n\n" + "\n".join(rendered) + "\n\n"
    text = "".join(convert(child, base, depth) for child in node.children)
    if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        return "\n\n" + "#" * int(name[1]) + " " + re.sub(r"\s+", " ", text).strip() + "\n\n"
    if name == "a":
        href = safe_link(base, node.get("href", ""))
        if node.get("href") and href and text.strip():
            return f"[{text.strip()}]({href.replace(' ', '%20').replace(')', '%29')})"
        return text
    if name == "code":
        code = node.get_text().strip()
        fence = "``" if "`" in code else "`"
        return fence + code + fence
    if name in {"strong", "b"}:
        return f"**{text.strip()}**" if text.strip() else ""
    if name in {"em", "i"}:
        return f"*{text.strip()}*" if text.strip() else ""
    if name == "br":
        return "\n"
    if name == "hr":
        return "\n\n---\n\n"
    if name == "img":
        return node.get("alt", "")
    if name == "blockquote":
        return "\n\n" + "\n".join("> " + line for line in text.strip().splitlines()) + "\n\n"
    if name in {"p", "div", "section", "article", "main", "dl", "dt", "dd", "details", "summary"}:
        return "\n\n" + text.strip() + "\n\n"
    return text


def chunk_markdown(markdown: str, url: str, limit: int = 1800) -> list[dict]:
    sections = []
    heading = "Document"
    buffer = []
    fence = None
    for line in markdown.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            run, suffix = marker.groups()
            if fence is None:
                fence = run
            elif run[0] == fence[0] and len(run) >= len(fence) and not suffix.strip():
                fence = None
        if fence is None and re.match(r"^#{1,6} ", line):
            if buffer:
                sections.append((heading, "\n".join(buffer).strip()))
            heading = re.sub(r"^#+ ", "", line)
            buffer = [line]
        else:
            buffer.append(line)
    if buffer:
        sections.append((heading, "\n".join(buffer).strip()))
    chunks = []
    repeats = Counter()
    for heading, section in sections:
        while section:
            end = min(len(section), limit)
            if end < len(section):
                boundary = max(section.rfind("\n", 0, end), section.rfind(" ", 0, end))
                if boundary > limit // 2:
                    end = boundary
            text, section = section[:end].strip(), section[end:].strip()
            if not text:
                continue
            content_hash = digest(text)
            identity = f"{url}\n{heading}\n{content_hash}"
            occurrence = repeats[identity]
            repeats[identity] += 1
            chunks.append({"id": digest(f"{identity}\n{occurrence}")[:24], "sourceUrl": url, "heading": heading,
                "index": len(chunks), "text": text, "contentHash": content_hash})
    return chunks


def extract_document(html: str, url: str, config: RunConfig, *, base_url: str | None = None) -> dict:
    base = base_url or url
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    canonical = soup.find("link", rel=lambda value: value and "canonical" in value)
    canonical_url = safe_link(base, canonical.get("href", "")) if canonical else None
    links = list(dict.fromkeys(value for a in soup.find_all("a", href=True) if (value := safe_link(base, a["href"]))))
    for node in list(soup.select("script,style,noscript,nav,header,footer,aside,svg,canvas,template,form,[role='navigation']")):
        node.decompose()
    for selector in config.exclude_css_selectors:
        for node in list(soup.select(selector)):
            if node.parent:
                node.decompose()
    if config.content_css_selector:
        root = soup.select_one(config.content_css_selector)
        if root is None:
            return {"markdown": "", "skipReason": "content_selector_not_found", "links": links}
    else:
        root = soup.select_one("main") or soup.select_one("article") or soup.select_one("[role='main']") or soup.body or soup
    markdown = normalize_markdown(convert(root, base))
    lower = title.lower()
    if any(value in lower for value in ("just a moment", "access denied", "verify you are human", "attention required")):
        return {"markdown": "", "skipReason": "browser_challenge", "links": links}
    if len(markdown) < config.min_text_length or (len(markdown) < 300 and re.search(r"enable javascript|javascript (?:is )?required", markdown, re.I)):
        return {"markdown": "", "skipReason": "insufficient_content", "links": links}
    if len(markdown) > config.max_text_chars:
        return {"markdown": "", "skipReason": "content_truncated", "links": links}
    chunks = chunk_markdown(markdown, url, config.chunk_size)
    if len(chunks) > config.max_chunks:
        return {"markdown": "", "skipReason": "chunk_limit", "links": links}
    return {"title": title, "canonicalUrl": canonical_url, "markdown": markdown, "contentHash": digest(markdown),
        "chunks": chunks, "links": links, "truncated": False}
