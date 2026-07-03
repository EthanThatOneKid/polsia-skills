# Polsia docs

[![skills.sh](https://skills.sh/b/wazootech/wiki)](https://skills.sh/wazootech/wiki)

Nightly-synced public source maps for Polsia.

## What it does

This repository mirrors Polsia public content into markdown files on a nightly schedule.

The scraper starts from the public sitemap at `https://polsia.com/sitemap.xml`, fetches each listed page, and writes a stable markdown snapshot plus a manifest of what was collected and what was skipped.

## Output layout

- `references/upstream/pages/` — generated markdown snapshots, one file per URL
- `references/upstream/manifest.json` — content-addressed manifest for the latest scrape
- `scripts/sync_polsia_sources.py` — scraper used by GitHub Actions

## Notes

- There is no `llms.txt` or `llms-full.txt` on Polsia today.
- The sitemap is the source of truth for what gets scraped.
- Pages that do not yield useful text are recorded as skips instead of failing the whole nightly run.
