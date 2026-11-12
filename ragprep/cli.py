"""Command line: `ragprep ingest DIR --db index.sqlite` and `ragprep search "question" --db index.sqlite`."""

from __future__ import annotations

import argparse
from dataclasses import asdict

from ragprep.index import Index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ragprep")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest", help="sync a folder of .md/.txt files into the index")
    ingest.add_argument("folder")
    search = sub.add_parser("search", help="semantic search over the index")
    search.add_argument("query")
    search.add_argument("-k", type=int, default=3)
    for p in (ingest, search):
        p.add_argument("--db", default="ragprep.sqlite")
    args = parser.parse_args(argv)

    index = Index(args.db)
    if args.command == "ingest":
        stats = index.sync_folder(args.folder)
        print(" ".join(f"{k}={v}" for k, v in asdict(stats).items()))
        print(" ".join(f"{k}={v}" for k, v in index.counts().items()))
    else:
        for hit in index.search(args.query, k=args.k):
            print(f"{hit.score:.3f}  {hit.chunk_id}\n       {hit.text[:160]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
