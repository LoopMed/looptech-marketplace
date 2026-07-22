"""Command-line entrypoint: `python -m memory_graph <reindex|search|get|neighbors|serve>`."""

from __future__ import annotations

import argparse
import json
import os
import sys

from .config import resolve_db_path, resolve_memory_dir
from .embed import Embedder
from .index import ensure_fresh
from .index import reindex as run_reindex
from .search import get as run_get
from .search import neighbors as run_neighbors
from .search import search as run_search
from .store import Store


def _add_db_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--db",
        default=None,
        help="Path to the SQLite index (default: $MEMORY_GRAPH_DB, else a "
        "path auto-derived from the current Claude Code project)",
    )


def _resolve_db(args: argparse.Namespace) -> str:
    return resolve_db_path(args.db)


def cmd_reindex(args: argparse.Namespace) -> int:
    directory = resolve_memory_dir(args.dir, required=True)
    db_path = _resolve_db(args)
    stats = run_reindex(directory, db_path)
    print(json.dumps(stats, indent=2))
    print(
        f"Indexed {stats['total']} memories "
        f"({stats['embedded']} embedded, {stats['skipped']} unchanged, "
        f"{stats['removed']} removed) -> {db_path}",
        file=sys.stderr,
    )
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    store = Store(_resolve_db(args))
    try:
        ensure_fresh(store, resolve_memory_dir(required=False))
        results = run_search(store, Embedder(), args.query, args.k)
    finally:
        store.close()
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    store = Store(_resolve_db(args))
    try:
        ensure_fresh(store, resolve_memory_dir(required=False))
        doc = run_get(store, args.name)
    finally:
        store.close()
    if doc is None:
        print(f"not found: {args.name}", file=sys.stderr)
        return 1
    print(json.dumps(doc, indent=2, ensure_ascii=False))
    return 0


def cmd_neighbors(args: argparse.Namespace) -> int:
    store = Store(_resolve_db(args))
    try:
        ensure_fresh(store, resolve_memory_dir(required=False))
        result = run_neighbors(store, args.name, args.depth)
    finally:
        store.close()
    if result["resolved"] is None:
        print(f"not found: {args.name}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    if args.dir:
        os.environ["MEMORY_GRAPH_DIR"] = args.dir
    if args.db:
        os.environ["MEMORY_GRAPH_DB"] = args.db
    from .server import main as serve_main

    serve_main()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="memory_graph")
    sub = parser.add_subparsers(dest="command", required=True)

    p_reindex = sub.add_parser("reindex", help="Scan a directory and (re)build the index")
    p_reindex.add_argument(
        "--dir",
        default=None,
        help="Directory of memory .md files (default: $MEMORY_GRAPH_DIR, else "
        "auto-detected from the current Claude Code project)",
    )
    _add_db_arg(p_reindex)
    p_reindex.set_defaults(func=cmd_reindex)

    p_search = sub.add_parser("search", help="Semantic search over indexed memories")
    p_search.add_argument("query")
    p_search.add_argument("--k", type=int, default=5)
    _add_db_arg(p_search)
    p_search.set_defaults(func=cmd_search)

    p_get = sub.add_parser("get", help="Fetch a single memory by name")
    p_get.add_argument("name")
    _add_db_arg(p_get)
    p_get.set_defaults(func=cmd_get)

    p_neighbors = sub.add_parser("neighbors", help="Follow [[links]] from a memory")
    p_neighbors.add_argument("name")
    p_neighbors.add_argument("--depth", type=int, default=1)
    _add_db_arg(p_neighbors)
    p_neighbors.set_defaults(func=cmd_neighbors)

    p_serve = sub.add_parser("serve", help="Run the MCP server (stdio)")
    p_serve.add_argument("--dir", default=None, help="Default memory directory for memory_reindex")
    _add_db_arg(p_serve)
    p_serve.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
