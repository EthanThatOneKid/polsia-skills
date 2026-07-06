#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_SITE_MAP_URL = "https://polsia.com/sitemap.xml"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "skills" / "polsia" / "references" / "upstream" / "pages"
DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "skills" / "polsia" / "references" / "upstream" / "manifest.json"

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


@dataclass(frozen=True)
class Page:
    url: str
    title: str
    body: str
    source_hash: str


@dataclass(frozen=True)
class Skip:
    url: str
    reason: str


def fetch(url: str, timeout: int = 30) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return data.decode(charset, errors="replace")


def fetch_bytes(url: str, timeout: int = 30) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/xml,text/xml,*/*;q=0.8"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_sitemap_urls(xml_text: str) -> list[str]:
    urls = re.findall(r"<loc>(.*?)</loc>", xml_text, flags=re.IGNORECASE | re.DOTALL)
    return [html.unescape(url.strip()) for url in urls if url.strip()]


def html_to_text(html_text: str) -> tuple[str, str]:
    title_match = re.search(r"<title>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
    title = normalize_whitespace(html.unescape(title_match.group(1))) if title_match else ""

    blocks = []
    body_match = re.search(r"<body[^>]*>(.*?)</body>", html_text, flags=re.IGNORECASE | re.DOTALL)
    body = body_match.group(1) if body_match else html_text
    body = re.sub(r"(?is)<(script|style|noscript|svg|iframe|canvas|meta|link)[^>]*>.*?</\1>", " ", body)
    body = re.sub(r"(?is)<br\s*/?>", "\n", body)
    body = re.sub(r"(?is)</(p|div|section|article|main|header|footer|li|h[1-6]|tr|table|ul|ol)>", "\n", body)
    body = re.sub(r"(?is)<[^>]+>", " ", body)
    body = html.unescape(body)
    for line in body.splitlines():
        line = normalize_whitespace(line)
        if line:
            blocks.append(line)
    return title, "\n\n".join(blocks)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slugify_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.strip("/") or "index"
    safe = re.sub(r"[^A-Za-z0-9._/-]+", "-", path)
    safe = safe.replace("/", "__")
    return f"{safe}.md"


def parse_pages(site_map_url: str) -> tuple[list[Page], list[Skip]]:
    sitemap = fetch(site_map_url)
    urls = extract_sitemap_urls(sitemap)
    pages: list[Page] = []
    skips: list[Skip] = []
    for url in urls:
        try:
            html_text = fetch(url)
        except urllib.error.HTTPError as exc:
            skips.append(Skip(url, f"http {exc.code}"))
            continue
        except Exception as exc:  # noqa: BLE001
            skips.append(Skip(url, f"fetch failed: {exc}"))
            continue

        title, text = html_to_text(html_text)
        if not text:
            skips.append(Skip(url, "empty text"))
            continue
        if len(text.split()) < 10:
            skips.append(Skip(url, "too little text"))
            continue
        source_hash = content_hash(html_text)
        pages.append(Page(url=url, title=title or url, body=text, source_hash=source_hash))
    return pages, skips


def write_page(output_dir: Path, page: Page) -> Path:
    parsed = urllib.parse.urlparse(page.url)
    filename = slugify_url(page.url)
    path = output_dir / filename
    content = [
        f"source: {page.url}",
        f"title: {page.title}",
        f"source_hash: {page.source_hash}",
        "",
        f"# {page.title}",
        "",
        page.body,
        "",
    ]
    path.write_text("\n".join(content), encoding="utf-8")
    return path


def prune_stale_files(output_dir: Path, keep: set[Path]) -> list[Path]:
    removed: list[Path] = []
    if not output_dir.exists():
        return removed
    for path in output_dir.glob("*.md"):
        if path not in keep:
            path.unlink()
            removed.append(path)
    return removed


def build_manifest(site_map_url: str, pages: list[Page], skips: list[Skip]) -> dict:
    return {
        "source": {"site_map_url": site_map_url},
        "count": len(pages),
        "skip_count": len(skips),
        "pages": [
            {"url": page.url, "title": page.title, "source_hash": page.source_hash, "filename": slugify_url(page.url)}
            for page in pages
        ],
        "skips": [{"url": skip.url, "reason": skip.reason} for skip in skips],
    }


def sync(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    manifest_path = Path(args.manifest)

    pages, skips = parse_pages(args.site_map_url)
    if not pages:
        print("No pages collected.", file=sys.stderr)
        return 1

    if args.dry_run:
        print(json.dumps(build_manifest(args.site_map_url, pages, skips), indent=2))
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    keep: set[Path] = set()
    for page in pages:
        keep.add(write_page(output_dir, page))
    removed = prune_stale_files(output_dir, keep)
    manifest = build_manifest(args.site_map_url, pages, skips)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {len(keep)} markdown files to {output_dir}")
    if removed:
        print(f"Removed {len(removed)} stale markdown files")
    if skips:
        print(f"Skipped {len(skips)} pages", file=sys.stderr)
    print(f"Manifest: {manifest_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Polsia public sitemap sources.")
    parser.add_argument("--site-map-url", default=DEFAULT_SITE_MAP_URL)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return sync(args)


if __name__ == "__main__":
    raise SystemExit(main())
