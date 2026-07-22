# Lanes (S/M/L) e o Delegation Mandate

O `workflow-dev` mantém o esqueleto de fases — discover → brainstorm → spec+plan → env →
impl → review → lint/tests → PR, com worktrees e pipeline de review — mas **zero
paths/comandos hardcoded**: tudo resolvido via `project-profile.md`. Este documento cobre o
sizing por lane e a regra dura que governa quem executa cada tipo de ação.

## Fase 0 — Resolver Project Profile

Antes de classificar a lane, o orquestrador lê o `CLAUDE.md` do projeto, monta
`path → stack → comandos` a partir do Project Profile e detecta stacks ausentes por
manifesto (ver `project-profile.md`). Nenhuma lane é classificada sem essa resolução prévia.

## Dispatch de expert

Para cada sub-projeto tocado pela task:

- Carrega a skill expert da stack resolvida.
- Se a task tocar a camada de persistência/banco de dados, carrega **também** a skill de
  banco de dados agnóstica.
- Para frontend, carrega a skill de **engenharia** (ex.: `expert-frontend-react`) **+** a
  skill de **UX** resolvida por área (`ux_overrides`/`ux_default` → skill mobile-first ou
  web-first; ambas se a task cruzar áreas — ver `project-profile.md`).

Todo template de subagente despachado a partir daqui referencia `subagent-handoff.md` e,
para tarefas de dev/debug/investigação, também `autonomy-react-loop.md` — colando o
conhecimento expert de arquitetura relevante. Critérios de sucesso (`success-criteria.md`)
são obrigatórios na entrada de toda spec/plan.

A fase de lint/tests roda os comandos declarados no Project Profile — nunca comandos
hardcoded do plugin — mantendo dois princípios: **reproduza localmente cada check que o CI
roda** e **lint só-linhas-novas quando for essa a forma que o CI usa**.

---

## Delegation Mandate — o agente principal é PURO ORQUESTRADOR

Regra dura, acima de qualquer lane: **o agente principal nunca faz análise de código,
implementação, ajuste ou ajuste pós-review por conta própria — tudo é delegado a
subagente.**

| Ação | Quem faz |
|------|----------|
| Análise/investigação de código, mapeamento, blast radius | **subagente** (handoff rico + ReAct) |
| Implementação de qualquer task (inclusive lane S) | **subagente** dev |
| Ajustes pós-review (aplicar CHANGES-REQUESTED) | **subagente** dev |
| Code review de todo diff | **subagente** reviewer |
| **Edição trivial ≤ 100 caracteres** (typo, bump de versão, uma linha de config) | orquestrador pode fazer direto |
| Coordenação: ler Project Profile, classificar lane, colar contexto, despachar, coletar síntese | orquestrador |
| Rodar comandos de verificação/git (test/lint/build, commit, push, abertura de PR) | orquestrador (executa o comando; **a análise de falha e o fix vão para subagente**) |

A única exceção ao mandato é a **edição trivial ≤ 100 caracteres** — um typo, um bump de
versão, uma linha de config isolada. Qualquer coisa além disso, mesmo que pareça pequena,
vai para um subagente dev com handoff rico.

## Sizing das lanes

O tamanho da lane define a **ceremônia** (quanto planejamento formal precede a implementação)
— nunca quem implementa. Implementação é **sempre** delegada a subagente, em toda lane.

### Lane S — mudança pequena e localizada
Poucos arquivos, sem cruzar sub-projeto, sem decisão de arquitetura em aberto. Mesmo assim:

- **Não existe "orquestrador implementa direto".** A implementação vai para **um subagente
  dev**, recebendo o handoff rico do diagnóstico que o orquestrador já levantou (o
  orquestrador pode ter feito a investigação inicial via subagente de análise, ou já ter
  contexto suficiente do Project Profile — mas quem escreve o código é o subagente dev).
- O review continua **obrigatório** antes do commit, mesmo em lane S.
- Spec/plan podem ser abreviados (modo rápido da skill de planejamento do projeto), mas os
  critérios de sucesso (`success-criteria.md`) continuam obrigatórios.

### Lane M — mudança de escopo médio
Múltiplos arquivos, possivelmente cruzando sub-projetos ou tocando a camada de dados. Spec e
plan formais, com critérios de sucesso testáveis por task. Implementação e review seguem o
mesmo pipeline de subagentes — o volume de handoffs cresce, não a regra de quem implementa.

### Lane L — mudança de escopo grande
Nova feature, mudança estrutural, ou risco alto (financeiro, segurança, dado sensível). Spec
e plan completos via a skill de planejamento do projeto, com fases explícitas de discover →
brainstorm → spec+plan → env → impl → review → lint/tests → PR. Cada task herda seu próprio
critério de "Done when". Pipeline de review roda em cada diff antes do commit correspondente,
não só no final.

## Loop de ajuste pós-review

Quando o subagente reviewer devolve `CHANGES-REQUESTED`:

1. **Novo subagente dev** aplica os ajustes, recebendo como Estado Atual o diff em questão
   mais os pontos levantados pelo review (handoff rico, não um resumo verbal).
2. Novo ciclo de review sobre o diff ajustado.
3. Só após aprovação o commit acontece.

O orquestrador **nunca** aplica o fix pós-review ele mesmo — mesmo que o ajuste pareça
trivial, a menos que caia dentro da exceção de ≤ 100 caracteres.

## Planejamento permanece desacoplado

A skill de spec/plan usada nas lanes M/L não é embutida no `workflow-dev` — o orquestrador
referencia a skill de planejamento que o projeto declarar (via Project Profile ou
`CLAUDE.md`), sem duplicar seu conteúdo aqui.
