#!/usr/bin/env python3
"""Import a BibTeX file into openbrain via the fetch_papers MCP tool.

For each entry we pick the best known-item identifier — DOI if present (also
recovered from a doi.org url), else the title — and hand them to openbrain's
fetch_papers in small serial batches with a pause between, to stay well under the
upstream citation-service rate limits (OpenAlex/Crossref/arXiv). fetch_papers
dedupes by DOI server-side, so re-running is safe.

Entries with no DOI and no title (e.g. unpublished "In Review" notes) have no
external record to fetch and are reported as skipped.

Usage:
  uv run python scripts/import_bibtex.py library.bib
  uv run python scripts/import_bibtex.py library.bib --batch-size 15 --pause 3
  uv run python scripts/import_bibtex.py library.bib --dois-only --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

# Run from the repo root so `src/` is importable without an install step.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from researcher.config import load_config  # noqa: E402
from researcher.openbrain import Openbrain  # noqa: E402

_DOI_PREFIX = re.compile(r"^https?://(?:dx\.)?doi\.org/", re.I)


def _field(entry: str, name: str) -> str | None:
    m = re.search(name + r"\s*=\s*[{\"]?(.+?)[}\"]?\s*,?\s*\n", entry, re.I)
    return m.group(1).strip() if m else None


def parse_bibtex(text: str) -> list[dict]:
    """Return one dict per entry: {key, doi, title, ident}. `ident` is the DOI if
    present, else the title, else None (nothing to look up)."""
    out: list[dict] = []
    for chunk in re.split(r"\n@", text):
        chunk = chunk.strip()
        if not chunk:
            continue
        if not chunk.startswith("@"):
            chunk = "@" + chunk
        km = re.match(r"@\w+\{([^,]+),", chunk)
        key = km.group(1).strip() if km else "?"
        doi = _field(chunk, "doi")
        url = _field(chunk, "url")
        title = _field(chunk, "title")
        if doi:
            doi = _DOI_PREFIX.sub("", doi.strip())
        elif url and "doi.org" in url:
            doi = _DOI_PREFIX.sub("", url.strip())
        ident = doi or title
        out.append({"key": key, "doi": doi, "title": title, "ident": ident})
    return out


def _chunks(seq: list, n: int):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Import a BibTeX file into openbrain.")
    ap.add_argument("bibfile", type=Path)
    ap.add_argument("--config-path", default="config.yaml")
    ap.add_argument("--batch-size", type=int, default=15, help="identifiers per fetch call")
    ap.add_argument("--pause", type=float, default=3.0, help="seconds to sleep between batches")
    ap.add_argument("--timeout", type=float, default=120.0, help="per-batch round-trip timeout (s)")
    ap.add_argument("--dois-only", action="store_true", help="skip title-only entries")
    ap.add_argument("--force", action="store_true", help="re-fetch/replace existing records")
    ap.add_argument("--dry-run", action="store_true", help="parse and plan, no fetch calls")
    args = ap.parse_args(argv)

    from dotenv import load_dotenv

    load_dotenv()  # OPENBRAIN_MCP_TOKEN

    entries = parse_bibtex(args.bibfile.read_text())
    fetchable = [e for e in entries if e["ident"] and (e["doi"] or not args.dois_only)]
    skipped = [e for e in entries if e not in fetchable]
    idents = [e["ident"] for e in fetchable]

    print(
        f"{len(entries)} entries: {len(idents)} to fetch "
        f"({sum(1 for e in fetchable if e['doi'])} by DOI, "
        f"{sum(1 for e in fetchable if not e['doi'])} by title), "
        f"{len(skipped)} skipped"
    )
    for e in skipped:
        why = "no DOI (--dois-only)" if e["ident"] else "no DOI/title"
        print(f"  skip {e['key']}: {why}")

    if args.dry_run:
        nbatches = (len(idents) + args.batch_size - 1) // args.batch_size
        print(f"\n[dry-run] would send {nbatches} batch(es) of <= {args.batch_size}")
        return 0

    cfg = load_config(Path(args.config_path))
    ob = Openbrain(
        cfg.openbrain_mcp_url, token=cfg.openbrain_mcp_token, ca_cert=cfg.openbrain_ca_cert
    )

    batches = list(_chunks(idents, args.batch_size))
    ok = 0
    for i, batch in enumerate(batches, 1):
        print(f"\nbatch {i}/{len(batches)} ({len(batch)} ids)...", flush=True)
        try:
            result = ob.fetch_papers(batch, force=args.force, timeout=args.timeout)
            ok += len(batch)
            print(f"  -> {result}")
        except Exception as exc:  # noqa: BLE001 — report and keep going
            print(f"  !! batch failed: {exc}", file=sys.stderr)
            print("     (re-run later; fetch_papers dedupes, so completed entries are skipped)")
        if i < len(batches):
            time.sleep(args.pause)

    print(f"\ndone: {ok}/{len(idents)} identifiers sent across {len(batches)} batch(es)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
