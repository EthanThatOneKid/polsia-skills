# Polsia docs and skill

[![skills.sh](https://skills.sh/b/ethanthatonekid/polsia-skills)](https://www.skills.sh/ethanthatonekid/polsia-skills)

Nightly-synced public source maps for Polsia.

## What it does

This repository mirrors Polsia public content into markdown files on a nightly schedule.

The scraper starts from the public sitemap at `https://polsia.com/sitemap.xml`, fetches each listed page, and writes a stable markdown snapshot plus a manifest of what was collected and what was skipped.

## Output layout

- `references/upstream/pages/` — generated markdown snapshots, one file per URL
- `references/upstream/manifest.json` — content-addressed manifest for the latest scrape
- `scripts/sync_polsia_sources.py` — scraper used by GitHub Actions
- `skills/polsia/SKILL.md` — consolidated master skill for the Polsia workflow
- `skills/polsia/references/upstream-notes.md` — upstream notes used by the skill

## Notes

- There is no `llms.txt` or `llms-full.txt` on Polsia today.
- The sitemap is the source of truth for what gets scraped.
- Pages that do not yield useful text are recorded as skips instead of failing the whole nightly run.
