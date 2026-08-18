#!/usr/bin/env bash
# Start memory-graph MCP (stdio). Hosts often resolve "./scripts/..." against the
# *workspace*, not the plugin — so this script locates the plugin root itself.
set -euo pipefail

plugin_root() {
  local c here cand
  for c in "${PLUGIN_ROOT:-}" "${CLAUDE_PLUGIN_ROOT:-}"; do
    if [ -n "$c" ] && [ -d "$c/memory_graph" ] && [ -f "$c/pyproject.toml" ]; then
      printf '%s\n' "$c"
      return 0
    fi
  done

  here="$(cd "$(dirname "$0")/.." && pwd)" 2>/dev/null || here=""
  if [ -n "$here" ] && [ -d "$here/memory_graph" ] && [ -f "$here/pyproject.toml" ]; then
    printf '%s\n' "$here"
    return 0
  fi

  # Newest install in Cursor / Claude plugin caches.
  shopt -s nullglob
  for cand in \
    "$HOME"/.cursor/plugins/cache/*/memory-graph/*/ \
    "$HOME"/.claude/plugins/cache/*/*/memory-graph/ \
    "$HOME"/.claude/plugins/cache/*/*/plugins/memory-graph/
  do
    if [ -d "${cand}memory_graph" ] && [ -f "${cand}pyproject.toml" ]; then
      printf '%s\n' "${cand%/}"
      return 0
    fi
  done

  return 1
}

if ! command -v uv >/dev/null 2>&1; then
  echo "memory-graph: 'uv' is required. Install: https://docs.astral.sh/uv/" >&2
  exit 1
fi

ROOT="$(plugin_root)" || {
  echo "memory-graph: could not find the plugin root (PLUGIN_ROOT unset, and no cache copy)." >&2
  exit 1
}

exec uv run --directory "$ROOT" python -m memory_graph serve
