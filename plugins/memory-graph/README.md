# memory-graph

A small, **100% local** MCP server + CLI that turns a directory of markdown
memory files into something you can actually query: **semantic (vector)
recall** and **graph traversal** over the `[[wikilinks]]` between memories.

Markdown is always the source of truth. The SQLite index (`.db`) is a
disposable, derived artifact — delete it any time and `reindex` rebuilds it.
The tool never edits your `.md` files.

## 100% local — zero cloud

- Embeddings are computed on-device with [fastembed](https://github.com/qdrant/fastembed)
  using the `BAAI/bge-small-en-v1.5` ONNX model.
- The **first** `reindex` run downloads that model's weights once (from
  Hugging Face) and caches them on disk. **Every run after that — every
  `reindex` and every `search`/`get`/`neighbors` — makes zero network
  calls.** This was verified by running `search` with `HTTP_PROXY`/
  `HTTPS_PROXY` pointed at an unreachable address: it still returns correct
  results.
- The vector/graph store is a local SQLite file. No data, query, or memory
  content is ever sent anywhere.

## Auto-reindex + auto-detection — you never reindex by hand

- **Lazy auto-reindex on every query.** `search`, `get` and `neighbors` — CLI
  and MCP tools alike — call the same incremental reindex used by the
  explicit `reindex` command before answering. Only `.md` files whose
  content hash changed since the last run get re-embedded, so the cost is
  ~ms when nothing changed. Edit a memory file and immediately search
  again — no `reindex` step in between required. `reindex`/`memory_reindex`
  still exist for an explicit/manual refresh, but nothing depends on you
  remembering to run them.
- **Auto-detected memory directory.** When `MEMORY_GRAPH_DIR` isn't set, the
  directory is derived from the current Claude Code project:
  `~/.claude/projects/<slug>/memory`, where `<slug>` is the project's
  absolute path with every `/` replaced by `-` (e.g.
  `/Users/you/projects/Foo` -> `-Users-you-projects-Foo`). Resolution order
  is explicit flag (where one exists) -> `$MEMORY_GRAPH_DIR` ->
  `$CLAUDE_PROJECT_DIR` (or `cwd`) via that slug rule. If nothing resolves,
  commands that require a directory (like `reindex`) fail with a message
  telling you to set `MEMORY_GRAPH_DIR`; query commands degrade gracefully
  and just search whatever's already indexed.
- **Auto-detected index location.** Likewise, when `MEMORY_GRAPH_DB` isn't
  set, the SQLite index lives at a stable, project-scoped path *outside*
  the memory directory: `~/.claude/projects/<slug>/.memory-graph/index.db`
  — so it never pollutes the memory folder and each project gets its own
  index automatically.

All of this lives in one place, `memory_graph/config.py`, used by every
entrypoint (`cli.py` and `server.py`) — no duplicated resolution logic.

## Memory file format

```markdown
---
name: <id>              # canonical ID — [[links]] elsewhere target this
description: <one line>
metadata:
  type: user | feedback | project | reference
---
Body markdown. Reference other memories as [[other-name]].
```

`name:` is the ID. Real-world corpora are messy though (a memory's `name:`
sometimes drifts from its filename, and `[[link]]` slugs sometimes target
the filename instead of the current `name:`) — every lookup (`get`,
`neighbors`, and link resolution during `reindex`) therefore tries, in
order: **exact `name` match → filename stem match → normalized
(case/hyphen/underscore-insensitive) match** before giving up. This makes
`neighbors project_doctor_payout_model` resolve correctly even when the
file's actual `name:` is `loopmed-doctor-payout-model-real-economics`.

## Install

```bash
cd plugins/memory-graph
uv venv .venv && uv pip install --python .venv/bin/python -e ".[dev]"
# or: python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
```

## CLI

```bash
# (Re)build the index explicitly. Incremental: only changed files are
# re-embedded (tracked by content hash), so repeated runs are fast. --dir
# is optional — see auto-detection above.
python -m memory_graph reindex --dir /path/to/memory

# Semantic search — ranked by embedding similarity, not keyword matching.
# Lazily reindexes first (see auto-reindex above), no --dir needed.
python -m memory_graph search "gateway de pagamento" --k 5

# Fetch one memory by name (or filename). Also lazily reindexes first.
python -m memory_graph get project_doctor_payout_model

# Follow the [[link]] graph (undirected: both outgoing and incoming links).
# Also lazily reindexes first.
python -m memory_graph neighbors project_doctor_payout_model --depth 1

# Run the MCP server (stdio transport).
python -m memory_graph serve --dir /path/to/memory
```

All commands accept `--db <path>` to point at a specific index file;
otherwise it's auto-detected (see above). `serve` also accepts `--dir` (or
`$MEMORY_GRAPH_DIR`) as the default directory for the `memory_reindex` tool.

## MCP tools

Exposed via `python -m memory_graph serve` (FastMCP, stdio):

| Tool | What it does |
|---|---|
| `memory_search(query, k=5)` | Semantic similarity search — finds conceptually related memories even without shared keywords. |
| `memory_get(name)` | Fetch one memory by name/filename. |
| `memory_neighbors(name, depth=1)` | Traverse the `[[link]]` graph from a memory, in both directions, out to `depth` hops. |
| `memory_reindex(directory=None)` | Re-scan the memory directory; only re-embeds files whose content changed. |

### Plugging into Claude Code

`.claude-plugin/plugin.json` declares the MCP server (`python -m memory_graph
serve`). Set `MEMORY_GRAPH_DIR` to your memory directory and (optionally)
`MEMORY_GRAPH_DB` for the index location before Claude Code launches the
plugin, e.g. in your shell profile or the plugin's env block.

## Storage backend

Vector search prefers [`sqlite-vec`](https://github.com/asg017/sqlite-vec)
(a loadable SQLite extension, cosine distance) and automatically falls back
to brute-force NumPy cosine similarity — computed in-process over embeddings
stored as BLOBs — if the extension can't be loaded (common on some Python
builds where `sqlite3.enable_load_extension` is unavailable). At the scale
of a personal memory corpus (tens to low thousands of files) both paths are
effectively instant. `Store.use_vec` tells you which backend is active.

## Tests

```bash
python -m pytest tests/
```

Covers frontmatter/link parsing and an end-to-end index → search → neighbors
flow against real fixture memories (using the real local embedding model —
no mocks — so a pass is a genuine correctness signal).

## Layout

```
memory_graph/
  model.py    MemoryDoc dataclass
  parse.py    frontmatter + [[link]] extraction (reads .md, never writes)
  embed.py    local fastembed wrapper
  store.py    SQLite: docs, links, vector search, name resolution
  config.py   resolve_memory_dir() / resolve_db_path() — the ONE place
              auto-detection lives, used by cli.py and server.py
  index.py    reindex(): parse -> (changed only) embed -> store;
              ensure_fresh(): lazy incremental reindex called at the top
              of every search/get/neighbors entrypoint
  search.py   search() / get() / neighbors()
  server.py   FastMCP server (4 tools)
  cli.py      argparse CLI
```
