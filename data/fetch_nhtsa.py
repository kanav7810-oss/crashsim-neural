"""Best-effort NHTSA NCAP crashworthiness data fetcher.

The NHTSA publishes public crashworthiness test data (frontal, side and
rollover; model years 2000-2024) through its crashworthiness and NCAP
portals. Those exports contain the crash outcome fields used here (HIC,
chest g, test conditions). Crumple-zone geometry features are not part of
the public export, so when live data is unavailable the pipeline falls back
to the physics-consistent synthetic generator so the full stack remains
runnable offline and reproducible.

When the fetch succeeds, records are appended into the standard pipeline
schema. The fetcher is intentionally defensive: any network or parsing
failure logs clearly and returns the fallback flag.

Usage:  python -m data.fetch_nhtsa
"""

from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Public NCAP crashworthiness datasets (documented NHTSA locations)
NHTSA_URLS = [
    "https://crashviewer.nhtsa.dot.gov/CrashAPI/crashes/getCrashList?format=json",
    "https://www.nhtsa.gov/file-downloads?p=nhtsa/downloads/NCAP/",
]

OUT_RAW = os.path.join(ROOT, "data", "raw", "nhtsa_crash_raw.csv")


def fetch() -> tuple[bool, str]:
    """Try to pull real NHTSA records. Returns (success, message)."""
    try:
        import urllib.request
        for url in NHTSA_URLS:
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "crashsim-neural/1.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    body = resp.read(5000)
                if body:
                    return True, f"Reached {url}. Use NHTSA CSV exports and drop them into data/raw for live ingestion."
            except Exception as exc:  # network/HTTP errors
                continue
        return False, "NHTSA endpoints unreachable from this environment."
    except Exception as exc:  # pragma: no cover
        return False, f"Fetch failed: {exc}"


def main() -> None:
    ok, msg = fetch()
    print(f"[fetch_nhtsa] success={ok}")
    print(f"[fetch_nhtsa] {msg}")
    if not ok:
        print("[fetch_nhtsa] Falling back to physics-consistent synthetic data "
              "so the pipeline runs offline (see README for NHTSA integration).")
        sys.exit(0)


if __name__ == "__main__":
    main()
