#!/usr/bin/env python3
"""Scrape reviews from Play Store, App Store, and Reddit into ChromaDB."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings
from app.db.chroma_client import ChromaReviewStore
from app.ingestion.pipeline import IngestionPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest reviews into ChromaDB")
    parser.add_argument("--count", type=int, default=None, help="Reviews per source")
    parser.add_argument("--sample", action="store_true", help="Load bundled sample reviews")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scrape Play Store, App Store, and Reddit (default when no flags)",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=["play_store", "app_store", "reddit"],
        help="Specific sources to scrape",
    )
    args = parser.parse_args()

    if args.sample:
        sources = None
        use_sample = True
    elif args.sources:
        sources = args.sources
        use_sample = False
    else:
        sources = ["play_store", "app_store", "reddit"]
        use_sample = False

    settings = get_settings()
    store = ChromaReviewStore(settings)
    pipeline = IngestionPipeline(settings, store)
    result = pipeline.run(count=args.count, use_sample=use_sample, sources=sources)
    print(result["message"])
    if result.get("by_source"):
        print("By source:", result["by_source"])


if __name__ == "__main__":
    main()
