#!/usr/bin/env bash
# Launch the memory-graph MCP server from the plugin root.
# Hosts expand PLUGIN_ROOT / CLAUDE_PLUGIN_ROOT; this script does not need them —
# it resolves its own directory so stdio MCP works on Claude, Codex, and Cursor.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! command -v uv >/dev/null 2>&1; then
  echo "memory-graph: 'uv' is required to start the MCP server. Install: https://docs.astral.sh/uv/" >&2
  exit 1
fi

exec uv run --directory "$ROOT" python -m memory_graph serve
