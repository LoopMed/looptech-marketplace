# memory-graph

Memória de projeto num **vault Obsidian**, com **recall semântico (vetorial)** e
**travessia do grafo de `[[wikilinks]]`** — MCP server + CLI, **100% local**.

**Divisão de papéis:**

| Camada | Quem faz | Como |
|---|---|---|
| **Escrita** | `obsidian` CLI | `create` / `append` / `property:set` — mantém índice, backlinks e templates coerentes |
| **Leitura por significado** | este plugin (MCP/CLI) | `search` / `get` / `neighbors` sobre o mesmo vault |
| **Leitura por texto exato** | `obsidian` CLI | `search:context` / `read` / `backlinks` |

O vault (markdown) é sempre a fonte da verdade. O índice SQLite é artefato
derivado e descartável — apague quando quiser, `reindex` reconstrói.
**Este pacote nunca escreve nos seus `.md`.**

## Skills

| Skill | Quando |
|---|---|
| `memory-graph:memory-vault` | Uso diário — buscar antes de implementar, gravar ao terminar, taxonomia, formato de nome, política de segredo, armadilhas do CLI |
| `memory-graph:memory-vault-setup` | Primeira configuração — valida CLI/skill do Obsidian, cria o vault com o dev, grava o protocolo nos `CLAUDE.md`/`AGENTS.md`, encontra e migra memória legada |

Pré-requisito das duas: o **`obsidian` CLI** instalado e o **Obsidian aberto** — o CLI
conversa com o app rodando. Ver https://help.obsidian.md/cli

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
- **Auto-detected vault.** When `MEMORY_GRAPH_DIR` isn't set (or the host
  left the literal `${MEMORY_GRAPH_DIR}` placeholder), the directory is
  resolved in one place (`memory_graph/config.py`):
  1. Explicit flag / tool `directory` — must exist.
  2. `$MEMORY_GRAPH_DIR` — empty strings and unexpanded `${…}` placeholders
     are ignored so auto-detect still runs. A real path that is missing
     raises.
  3. Walk ancestors from the project dir up to `$HOME` (inclusive, never
     above HOME). At each level: (a) `memory.path` in `CLAUDE.md` or
     `AGENTS.md`, resolved relative to **that file's directory**; an
     existing dir is enough. (b) the level itself or an immediate child
     containing `.obsidian/` (dependency and hidden dirs skipped; a
     `*memory*`-named vault wins when several exist). First hit wins.
  4. Legacy `~/.claude/projects/<slug>/memory` **only if it contains at
     least one `.md`**. An empty harness directory does not count.
  5. If nothing resolves, commands that require a directory (like
     `reindex`) fail pointing at the setup skill; query commands degrade
     gracefully and search whatever's already indexed.
  Run `memory-graph:memory-vault-setup` to create a vault or migrate a
  pre-vault install.
- **Auto-detected index location.** Likewise, when `MEMORY_GRAPH_DB` isn't
  set, the SQLite index lives at a stable, project-scoped path *outside*
  the memory directory: `~/.looptech/memory-graph/<slug>/index.db`. If an
  older Claude-era index already exists at
  `~/.claude/projects/<slug>/.memory-graph/index.db`, that file is reused
  so an upgrade does not re-embed the vault.

All of this lives in one place, `memory_graph/config.py`, used by every
entrypoint (`cli.py` and `server.py`) — no duplicated resolution logic.

## Memory file format

Qualquer nota do vault é indexável. O frontmatter recomendado pela skill
`memory-graph:memory-vault`:

```markdown
---
titulo: <título humano>
tipo: projeto | referencia | decisao | feedback | spec | log | moc | sistema
produto: [<Produto>]
status: em-prod | ativo | em-andamento | pendente | arquivado
atualizado: AAAA-MM-DD
aliases: [<nome antigo>, <slug antigo>]   # mantém [[links]] antigos resolvendo
---
Corpo em markdown. Referencie outras notas como [[outra nota]].
```

O formato legado (`name:` / `description:` / `metadata.type:`) continua sendo
lido — a resolução de link aceita os dois.

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

### Plugging into Claude Code, Codex, and Cursor

The plugin is the same folder. Each host reads its own manifest:

| Host | Manifest | MCP config |
|---|---|---|
| Claude Code | `.claude-plugin/plugin.json` | inline `mcpServers` (kept for existing installs) |
| Codex | `.codex-plugin/plugin.json` | `.mcp.json` → `./scripts/serve.sh` |
| Cursor | `.cursor-plugin/plugin.json` | `mcp.json` → `./scripts/serve.sh` |

MCP launch is `bash -c` + `uv run --directory <plugin-root>` (not `./scripts/serve.sh`).
Cursor resolves relative commands against the **workspace**, so a `./scripts/...`
path becomes `<seu-projeto>/scripts/serve.sh` and fails with ENOENT. The launcher
uses `PLUGIN_ROOT` / `CLAUDE_PLUGIN_ROOT` when the host sets them, otherwise the
plugin cache. The vault
directory is auto-detected; set `MEMORY_GRAPH_DIR` / `MEMORY_GRAPH_DB` only to
override. On Cursor those names are optional plugin variables (Customize →
Configure). Reinicie a sessão depois de instalar para o MCP aparecer.

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
