# Host compatibility — Claude Code, Codex, Cursor

The same plugin ships to three hosts. Skills stay host-agnostic; only the
**invocation surface** and the **native tool names** change. Detect the host
once (from available tools / env) and keep that mapping for the rest of the
session.

## Detect the host

| Signal | Host |
|---|---|
| `Skill` tool, `CLAUDE_PLUGIN_ROOT`, `/plugin` slash commands | **Claude Code** |
| `spawn_agent` / `CODEX_HOME`, skills invoked with `$name` | **Codex** |
| Cursor `Task` tool, `.cursor/` project config, `/skill-name` | **Cursor** |
| Ambiguous | Prefer the host whose tools you actually have. Never invent a missing tool. |

## Project Profile — where it lives

The Profile is the same YAML/Markdown block on every host. **Read both files
when they exist; write both when you create or update it.**

| File | Who reads it |
|---|---|
| `CLAUDE.md` | Claude Code (and any host that also opens it) |
| `AGENTS.md` | Codex, Cursor, Gemini, Copilot |

- If only one file has the Profile, that file is authoritative. Copy it into
  the other file (create `AGENTS.md` if missing) so the next host does not
  start blind.
- If both have a Profile and they **diverge**, stop and ask which one wins
  before writing anything. Do not silently pick.
- Sub-project copies follow the same rule (`<sub>/CLAUDE.md` and
  `<sub>/AGENTS.md`).
- "Facts come from the Project Profile" always means **those files**, never
  a host-only settings panel.

## Load a skill

Do **not** hardcode a host-only invocation. Read the skill's `SKILL.md` and
follow it.

| Host | How the user / agent loads a skill |
|---|---|
| Claude Code | `Skill("looptech:<name>")` or `/looptech:<name>` |
| Codex | `$<name>` (e.g. `$workflow-dev`, `$init`) or auto-trigger from the description |
| Cursor | `/<name>` (plugin command or skill) |

Sibling plugin skills (`memory-graph:memory-vault`,
`memory-graph:memory-vault-setup`) load the same way after that plugin is
installed.

## Spawn a subagent

The Delegation Mandate does not change. Only the spawn API does. Resolve the
**role** first (`agent-roles.md`); then pass the resolved catalog ID through
the host's native field. Never put a vendor model name in the skill text.

| Host | Spawn | How the role ID is passed |
|---|---|---|
| Claude Code | native `Task` / subagent tool | `model` (and native effort if the host has one) from `agents.claude.<role>` or the catalog |
| Codex | native `spawn_agent` (or current equivalent) | per-child model if the host still allows it; else inherit the parent and **still spawn** |
| Cursor | native `Task` / named agent | spawn the plugin agent **by name** (`expert-backend-go`, `expert-security`, `plan`, `review`, …). `Task(model:)` is often rejected except for `fast`; named agents in the plugin `agents/` directory are the reliable path |

- Never skip a spawn because the host renamed the tool.
- Never tell a subagent to "go load the skill and read the plan files".
  Paste the handoff (`subagent-handoff.md`) into the child prompt.
- If the host cannot spawn at all, say so and stop — do not silently do the
  child's work in the parent (except the ≤ 100 character exception).
- If the host rejects the resolved ID, report, fall back to the session
  default, keep the role, continue.

## Restart wording

Say "restart this agent session" (Claude Code / Codex / Cursor), not
"restart Claude Code", unless you are giving a host-specific command.
