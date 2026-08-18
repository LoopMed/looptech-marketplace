# Agent roles — classes, never model slugs

The plugin knows **roles**. Model IDs belong in the Project Profile (`agents:`) or,
failing that, in whatever catalog the current host exposes. Never write a vendor
slug (a branded model name) into a skill.

## Roles

| Role | Class | When | What to pick from the host catalog |
|---|---|---|---|
| `orchestrator` | `coord` | Fase 0, 1 (git), 2 (chat), Env, 7, 8, Fechamento | Session default. Do not swap. |
| `plan` | `reasoning` | Fase 1b blast radius, Fase 3 spec+plan | Highest reasoning + longest context |
| `impl` | `code` | Fase 6/6-S dev, pós-review fix, Fase 7 fix | Fastest strong coding model |
| `review` | `critique` | Review de correção (Done when / diff) | A **different** ID from `impl` on this task, if the host has one |
| `security` | `security` | Review de segurança no mesmo diff, antes do commit | Host security specialist if any; else `critique` + the security checklist |

## Resolution (Fase 0, once per session)

1. Detect the host (`host-compat.md`).
2. If `agents.<host>.<role>` exists in the Profile, use that `model` (and any
   host-native effort/thinking field next to it).
3. Else, if `agents.<role>` exists without a host key, use that.
4. Else, scan the host's installed catalog and pick by **class** (table above).
5. If the catalog has **one** model, every role inherits it. Say so:
   `"um modelo só — papéis colapsados"`.
6. If `security` has no specialist, fall back to `critique` and paste
   `security-review.md` in full. Do **not** invent a product name.

Never invent a slug. If the host rejects the resolved ID, report, fall back to
the session default, and continue the spawn.

## Profile block

Optional. Without it the workflow still runs, using steps 4–6, and warns.

```yaml
agents:
  <host>:                    # cursor | claude | codex | … — only hosts you use
    reasoning: { model: <id do catálogo> }
    code:      { model: <id do catálogo> }
    critique:  { model: <id do catálogo> }   # omit → another code id, else reasoning readonly
    security:  { model: <id do catálogo> }   # omit → critique + checklist
```

`<id do catálogo>` is whatever the host lists **today**. The plugin never
suggests a default brand. `init` asks the human to map the catalog.

## Spawn

Pass the resolved ID through the host's native spawn (`host-compat.md`). Prefer
spawning a **named agent** when the host has one for that role; otherwise pass
the model field the host accepts. The handoff (`subagent-handoff.md`) does not
change — only who runs it.

The orchestrator never changes its own model mid-task.
