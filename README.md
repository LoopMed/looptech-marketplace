# looptech marketplace

Marketplace com **2 plugins** (`looptech`, `memory-graph`) que empacota o fluxo de
desenvolvimento da LoopTech como um **workflow agnóstico de produto**: orquestração
de tarefas de dev (spec → plano → implementação → review → PR) e um conjunto de
**skills expert** por stack/eixo, reutilizáveis em qualquer projeto — LoopMed, LoopCRM
ou um projeto futuro X/Y.

O mesmo repositório instala em **Claude Code**, **Codex** e **Cursor**. Cada host lê o
catálogo dele (`.claude-plugin/`, `.agents/plugins/`, `.cursor-plugin/`); a
implementação em `plugins/` é única.

A regra de ouro: **o plugin carrega processo e disciplina transferível; o Project
Profile de cada projeto (`CLAUDE.md` e `AGENTS.md`) carrega os fatos concretos**
(paths, comandos, branches, conexões de banco). Nenhuma skill deste plugin cita nomes
de produto, paths concretos ou nomes de conexão — isso garante que o mesmo plugin
sirva qualquer repositório. Claude Code lê `CLAUDE.md`; Codex e Cursor leem
`AGENTS.md`. O `looptech:init` grava o Profile nos dois.

## O que é o plugin `looptech`

Um único plugin, publicado neste marketplace, com **9 skills** expert + `init` e
**agentes nomeados** em `agents/` (mesmo nome da skill, spawnáveis no host):

1. `looptech:workflow-dev` — o **orquestrador**. Lê o Project Profile do `CLAUDE.md`
   do projeto, classifica o tamanho da tarefa (lane S/M/L), resolve qual(is) skill(s)
   expert carregar por sub-projeto tocado, e conduz o ciclo completo
   discover → brainstorm → spec+plan → implementação (agente expert da stack) →
   review de correção → review de segurança/pentest (`expert-security`) →
   lint/testes → PR.
   Atua como **puro orquestrador**: nunca implementa/analisa/ajusta código por conta
   própria (exceto edição trivial ≤ 100 caracteres) — tudo isso é delegado a subagentes,
   com handoff rico, loop de autonomia (ReAct) e critérios de sucesso obrigatórios.
2. `looptech:expert-backend-go` — engenharia Go: arquitetura em camadas/hexagonal,
   desacoplamento por interfaces, disciplina sqlx (query consts, zero `SELECT *`,
   parametrização), pirâmide de testes (unit + integração + injection), lint
   `only-new-issues`, segurança em princípio (ownership, locks financeiros, gating por
   ambiente).
3. `looptech:expert-backend-python` — engenharia Python (FastAPI + SQLAlchemy 2.0 async +
   Pydantic v2): arquitetura Clean + Hexagonal (Ports & Adapters via `ABC`), domínio puro
   sem ORM/Pydantic, disciplina SQLAlchemy async (`select()` tipado, zero `SELECT *`, valores
   só como parâmetro ligado, `text()` só com `:param`, `flush` no repo — `commit` na borda),
   pirâmide de testes (unit com ports mockados + integração com testcontainers + injection),
   gate `ruff` + `mypy` strict, segurança em princípio (ownership, locks transacionais,
   gating por ambiente).
4. `looptech:expert-frontend-react` — engenharia React + TypeScript: arquitetura de
   componentes, hooks testáveis, TypeScript estrito (sem `any`/`@ts-ignore` sem
   justificativa), testes com vitest + RTL focados em comportamento visível, E2E no
   golden path, CSP e segurança de cliente.
5. `looptech:expert-frontend-vue` — engenharia Vue 3 + TypeScript: SFCs com
   `<script setup>`, composables testáveis, TypeScript estrito (incl. `ref(null)` tipado),
   testes com vitest + Vue Testing Library focados em comportamento visível, E2E no
   golden path, CSP e segurança de cliente.
6. `looptech:expert-frontend-pwa` — eixo de **UX** orientado a mobile-first: layout
   mobile-first, alvos de toque ≥ 44px, densidade e ergonomia de polegar, performance
   percebida, comportamento offline-tolerante.
7. `looptech:expert-frontend-web` — eixo de **UX** orientado a web-first/desktop:
   layouts densos, hover e atalhos de teclado, tabelas/grades para telas grandes,
   fluxos de operador/admin.
8. `looptech:expert-database` — disciplina de query (query consts, zero `SELECT *`,
   parametrização, `null.T`, injection tests) **+** fluxo de execução operacional
   (preflight de conexão → discovery live de tabelas/schemas/indexes → query sargável
   → execução), gate de produção e migrations por existência (não por version).
9. `looptech:expert-security` — review de segurança e pentest **defensivo** do diff
   (superfície, threat model, tabela de dano à empresa, scanners do repo). Readonly.
   Sem exploit, sem probe em produção.

### Os dois eixos do frontend

`expert-frontend-react` e `expert-frontend-vue` cobrem **engenharia** (stack, arquitetura,
testes) — carregue a da stack do sub-projeto. `expert-frontend-pwa` e
`expert-frontend-web` cobrem **UX/UI/interação** — um eixo independente, por **área**
do produto, não por sub-projeto. As duas skills de UX não repetem engenharia: elas
assumem que a skill de engenharia já cobre arquitetura/TS/testes, e adicionam apenas a
orientação de interação (mobile-first ou web-first).

Elas **compõem**: uma tarefa de frontend carrega a skill de engenharia da stack +
a skill de UX resolvida pela área tocada (via `ux_default`/`ux_overrides` no Project
Profile — veja abaixo). Isso permite combinações como "React mobile-first", "Vue
web-first", etc., sem duplicar a disciplina de engenharia.

| Skill | Dispara quando... |
|---|---|
| `looptech:workflow-dev` | Início de qualquer tarefa de desenvolvimento (feature, fix, hotfix, refactor) num projeto com Project Profile |
| `looptech:expert-backend-go` | A tarefa toca um sub-projeto mapeado como stack Go no Project Profile |
| `looptech:expert-backend-python` | A tarefa toca um sub-projeto mapeado como stack Python no Project Profile (ou inferido por `pyproject.toml`/`requirements.txt`) |
| `looptech:expert-frontend-react` | A tarefa toca um sub-projeto mapeado como stack React+TS no Project Profile |
| `looptech:expert-frontend-vue` | A tarefa toca um sub-projeto mapeado como stack Vue+TS no Project Profile (ou inferido por `package.json` com `vue`) |
| `looptech:expert-frontend-pwa` | A área tocada resolve para UX mobile-first (`ux_default`/`ux_overrides` apontando `expert-frontend-pwa`) |
| `looptech:expert-frontend-web` | A área tocada resolve para UX web-first (`ux_default`/`ux_overrides` apontando `expert-frontend-web`) |
| `looptech:expert-database` | A tarefa toca a camada de persistência/banco de dados de qualquer sub-projeto |
| `looptech:expert-security` | Review de segurança / pentest defensivo de todo diff de código (agente `expert-security`) |

## Como instalar

### Claude Code

```
/plugin marketplace add git@github.com:LoopMed/looptech-marketplace.git
/plugin install looptech@looptech
```

Skills ficam disponíveis como `looptech:<skill>` e `/looptech:init`.

### Codex

```
codex plugin marketplace add LoopMed/looptech-marketplace --ref main
codex plugin install looptech --source looptech
```

Skills disparam pelo description ou com `$init` / `$workflow-dev`. Depois:

```
codex plugin install memory-graph --source looptech
```

### Cursor

**Team marketplace** (Teams/Enterprise): Dashboard → Plugins → Import from Repo →
`https://github.com/LoopMed/looptech-marketplace`. O Cursor lê
`.cursor-plugin/marketplace.json` e lista `looptech` e `memory-graph`. Instale pelo
painel Customize.

**Local (dev / sem team marketplace):**

```
mkdir -p ~/.cursor/plugins/local
ln -s /caminho/para/looptech-marketplace/plugins/looptech ~/.cursor/plugins/local/looptech
ln -s /caminho/para/looptech-marketplace/plugins/memory-graph ~/.cursor/plugins/local/memory-graph
```

Reinicie o Cursor (Developer: Reload Window). Skills e commands (`/init`,
`/workflow-dev`) aparecem em Customize.

### Depois de instalar — rode o `init`

**Você não precisa decorar o que configurar.** Assim que instalar, rode:

| Host | Como disparar |
|---|---|
| Claude Code | `/looptech:init` |
| Codex | `$init` |
| Cursor | `/init` |

A skill `looptech:init` faz o setup guiado do zero ao pronto — detecta os sub-projetos e
gera o **Project Profile** no `CLAUDE.md` **e** no `AGENTS.md`, configura a conexão de
**banco** (via `looptech:expert-database`, sem gravar credencial silenciosamente e com
PROD sempre gated), mapeia os **papéis de agente** (`reasoning` / `code` / `critique` /
`security`) a partir do catálogo do host atual, oferece o **memory-graph** (memória
semântica local, opcional), e valida os **runtimes** de cada stack. Cada passo é
DETECTA → REPORTA → OFERECE (com sua confirmação). Reinicie a sessão ao final se um MCP
novo (memory-graph) tiver sido adicionado.

> Plugin irmão `memory-graph`: memória com recall vetorial + travessia de `[[links]]`,
> 100% local. Claude: `/plugin install memory-graph@looptech`. Codex/Cursor: instale
> `memory-graph` do mesmo marketplace (ou o symlink local acima). O `init` te guia por
> ele também.

## Como um projeto adota o plugin

Um projeto adota o `looptech:workflow-dev` colando um bloco **Project Profile** no
`CLAUDE.md` **e** no `AGENTS.md`. É o único ponto onde o projeto declara os fatos
concretos que o plugin precisa para operar: sub-projetos e suas stacks, o eixo de UX por
área, convenções de VCS, diretório de specs, comandos exatos por stack (espelhando o CI),
o mapa de papéis de agente (se houver) e, se houver banco, as conexões e o dialeto.
Claude Code lê `CLAUDE.md`; Codex e Cursor leem `AGENTS.md` — os dois arquivos precisam
do mesmo bloco.

Template genérico (adapte os valores de exemplo ao seu projeto):

```yaml
## Project Profile (looptech:workflow-dev)
subprojects:
  - { path: backend/,          stack: expert-backend-go }
  - path: frontend/
    stack: expert-frontend-react            # eixo de engenharia
    ux_default: expert-frontend-pwa         # app principal = mobile-first
    ux_overrides:                            # eixo de UX, por path (mais específico vence)
      - { match: "src/**/admin/**", ux: expert-frontend-web }   # admin = web-first
  - { path: service-b/,        stack: expert-backend-go }
  - path: admin-panel/
    stack: expert-frontend-react
    ux_default: expert-frontend-web          # painel admin = web-first / dark-first
  # fora do workflow (ad hoc): gateway, scripts, integrações internas
vcs:       { base: develop, pr_target: develop, prefixes: [feature, fix, hotfix], hotfix_base: main }
specs_dir: .specs/<feature>/
commands:
  expert-backend-go:
    test:  "go test ./..."
    integ: "go test -tags integration ./internal/infra/database/repositories/... -timeout 300s"
    lint:  "golangci-lint run --new-from-rev=origin/develop ./..."   # forma do CI; DEVE imprimir '0 issues'
    build: "go build ./..."
  expert-frontend-react:
    test:  "npm run test"
    lint:  "npm run lint"
    types: "npx tsc --noEmit"
    build: "npm run build"
database:
  connections: { stage: my-project-stage, prod: my-project-prod }   # nomes do profile de conexão
  dialect: postgres
  discovery: { tables: "\\dt", schema: "\\d <table>", indexes: "\\di <table>" }
  migrations_table: schema_migrations
ci_gotchas: |
  - lint = only-new-issues; linha modificada conta como nova
  - CI não roda integration; rodar local se tocar repo layer
agents:                                 # opcional; IDs vêm do catálogo do host
  <host>:                               # cursor | claude | codex
    reasoning: { model: <id> }          # spec/plan/blast radius
    code:      { model: <id> }          # implementação
    critique:  { model: <id> }          # review de correção (outro ID que não o code)
    security:  { model: <id> }          # review de segurança; omitir se o host não tiver
  - merge develop→staging deploy; merge main→prod deploy+tag
```

Notas sobre o Profile:

- O formato de referência é YAML, mas um projeto pode declarar o equivalente em tabela
  Markdown — o que importa é que `workflow-dev` consiga resolver: sub-projetos, stack
  por path, eixo de UX por área, comandos por stack, convenção de branch/PR,
  `specs_dir` e (se houver DB) o bloco `database`.
- Para um path ausente no Profile, `workflow-dev` infere a stack pelo manifesto
  (`go.mod` → `expert-backend-go`; `pyproject.toml`/`requirements.txt` → `expert-backend-python`;
  `package.json` com `react` → `expert-frontend-react`; com `vue` → `expert-frontend-vue`) e
  avisa que inferiu — o Profile é sempre a fonte autoritativa quando presente.
- Regras de **segurança do produto** (locks nomeados, gating de endpoints sensíveis,
  CORS/gateway, rate-limit, auth de storage) continuam no Project Profile do projeto —
  o plugin carrega apenas os princípios agnósticos correspondentes.
- Fatos de conexão de banco (nomes de profile stage/prod, dialeto, secret store,
  sinal visual de produção) também ficam no Project Profile — o `expert-database` é
  agnóstico ao dialeto (Postgres como referência).

## Estrutura do repositório

Um único `plugins/` e um catálogo por host — o mesmo padrão do marketplace oficial do Expo:

```
.claude-plugin/marketplace.json     # Claude Code
.agents/plugins/marketplace.json    # Codex
.cursor-plugin/marketplace.json     # Cursor
plugins/
  looptech/
    .claude-plugin/plugin.json
    .codex-plugin/plugin.json
    .cursor-plugin/plugin.json
    commands/                       # slash commands do Cursor (/init, /workflow-dev)
    agents/                         # agentes nomeados (experts + plan + review + security)
    skills/
  memory-graph/
    .claude-plugin/plugin.json
    .codex-plugin/plugin.json
    .cursor-plugin/plugin.json
    .mcp.json                       # Claude + Codex
    mcp.json                        # Cursor
    scripts/serve.sh                # stdio MCP, independente de CLAUDE_PLUGIN_ROOT
    skills/
```

Versões dos três manifests de cada plugin precisam andar juntas (`looptech` 0.6.0,
`memory-graph` 0.3.0).

## Extensibilidade

O naming por stack (`expert-backend-go`, `expert-backend-python`, `expert-frontend-react`,
`expert-frontend-vue`, ...) já deixa o caminho aberto para novas skills expert conforme
surgir necessidade real em algum projeto consumidor — por exemplo `expert-backend-node` ou
`expert-database-<outro dialeto>`. Essas skills são criadas quando um projeto real exigir,
seguindo o mesmo padrão: processo e disciplina transferível no plugin, fatos concretos no
Project Profile (`CLAUDE.md` / `AGENTS.md`) do projeto.

## Licença

MIT — veja [LICENSE](./LICENSE).
