# looptech marketplace

Marketplace Claude Code com **1 plugin** (`looptech`) que empacota o fluxo de
desenvolvimento da LoopTech como um **workflow agnóstico de produto**: orquestração
de tarefas de dev (spec → plano → implementação → review → PR) e um conjunto de
**skills expert** por stack/eixo, reutilizáveis em qualquer projeto — LoopMed, LoopCRM
ou um projeto futuro X/Y.

A regra de ouro: **o plugin carrega processo e disciplina transferível; o `CLAUDE.md`
de cada projeto carrega os fatos concretos** (paths, comandos, branches, conexões de
banco). Nenhuma skill deste plugin cita nomes de produto, paths concretos ou nomes de
conexão — isso garante que o mesmo plugin sirva qualquer repositório.

## O que é o plugin `looptech`

Um único plugin, publicado neste marketplace, com **6 skills**:

1. `looptech:workflow-dev` — o **orquestrador**. Lê o Project Profile do `CLAUDE.md`
   do projeto, classifica o tamanho da tarefa (lane S/M/L), resolve qual(is) skill(s)
   expert carregar por sub-projeto tocado, e conduz o ciclo completo
   discover → brainstorm → spec+plan → implementação → review → lint/testes → PR.
   Atua como **puro orquestrador**: nunca implementa/analisa/ajusta código por conta
   própria (exceto edição trivial ≤ 100 caracteres) — tudo isso é delegado a subagentes,
   com handoff rico, loop de autonomia (ReAct) e critérios de sucesso obrigatórios.
2. `looptech:expert-backend-go` — engenharia Go: arquitetura em camadas/hexagonal,
   desacoplamento por interfaces, disciplina sqlx (query consts, zero `SELECT *`,
   parametrização), pirâmide de testes (unit + integração + injection), lint
   `only-new-issues`, segurança em princípio (ownership, locks financeiros, gating por
   ambiente).
3. `looptech:expert-frontend-react` — engenharia React + TypeScript: arquitetura de
   componentes, hooks testáveis, TypeScript estrito (sem `any`/`@ts-ignore` sem
   justificativa), testes com vitest + RTL focados em comportamento visível, E2E no
   golden path, CSP e segurança de cliente.
4. `looptech:expert-frontend-pwa` — eixo de **UX** orientado a mobile-first: layout
   mobile-first, alvos de toque ≥ 44px, densidade e ergonomia de polegar, performance
   percebida, comportamento offline-tolerante.
5. `looptech:expert-frontend-web` — eixo de **UX** orientado a web-first/desktop:
   layouts densos, hover e atalhos de teclado, tabelas/grades para telas grandes,
   fluxos de operador/admin.
6. `looptech:expert-database` — disciplina de query (query consts, zero `SELECT *`,
   parametrização, `null.T`, injection tests) **+** fluxo de execução operacional
   (preflight de conexão → discovery live de tabelas/schemas/indexes → query sargável
   → execução), gate de produção e migrations por existência (não por version).

### Os dois eixos do frontend

`expert-frontend-react` cobre **engenharia** (stack, arquitetura, testes) e é sempre
carregada em qualquer tarefa de frontend React. `expert-frontend-pwa` e
`expert-frontend-web` cobrem **UX/UI/interação** — um eixo independente, por **área**
do produto, não por sub-projeto. As duas skills de UX não repetem engenharia: elas
assumem que a skill de engenharia já cobre arquitetura/TS/testes, e adicionam apenas a
orientação de interação (mobile-first ou web-first).

Elas **compõem**: uma tarefa de frontend carrega a skill de engenharia da stack +
a skill de UX resolvida pela área tocada (via `ux_default`/`ux_overrides` no Project
Profile — veja abaixo). Isso permite combinações como "React mobile-first" ou "React
web-first" sem duplicar a disciplina de engenharia, e deixa aberto o caminho para
futuras combinações (ex.: "Vue mobile-first") sem reescrever nada.

| Skill | Dispara quando... |
|---|---|
| `looptech:workflow-dev` | Início de qualquer tarefa de desenvolvimento (feature, fix, hotfix, refactor) num projeto com Project Profile |
| `looptech:expert-backend-go` | A tarefa toca um sub-projeto mapeado como stack Go no Project Profile |
| `looptech:expert-frontend-react` | A tarefa toca um sub-projeto mapeado como stack React+TS no Project Profile |
| `looptech:expert-frontend-pwa` | A área tocada resolve para UX mobile-first (`ux_default`/`ux_overrides` apontando `expert-frontend-pwa`) |
| `looptech:expert-frontend-web` | A área tocada resolve para UX web-first (`ux_default`/`ux_overrides` apontando `expert-frontend-web`) |
| `looptech:expert-database` | A tarefa toca a camada de persistência/banco de dados de qualquer sub-projeto |

## Como instalar

No Claude Code:

```
/plugin marketplace add git@github.com:LoopMed/looptech-marketplace.git
/plugin install looptech@looptech
```

Isso registra o marketplace `looptech` e instala o plugin `looptech`, disponibilizando
as 6 skills acima via `looptech:<skill>`.

## Como um projeto adota o plugin

Um projeto adota o `looptech:workflow-dev` colando um bloco **Project Profile** no seu
`CLAUDE.md`. É o único ponto onde o projeto declara os fatos concretos que o plugin
precisa para operar: sub-projetos e suas stacks, o eixo de UX por área, convenções de
VCS, diretório de specs, comandos exatos por stack (espelhando o CI) e, se houver banco,
as conexões e o dialeto.

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
  - merge develop→staging deploy; merge main→prod deploy+tag
```

Notas sobre o Profile:

- O formato de referência é YAML, mas um projeto pode declarar o equivalente em tabela
  Markdown — o que importa é que `workflow-dev` consiga resolver: sub-projetos, stack
  por path, eixo de UX por área, comandos por stack, convenção de branch/PR,
  `specs_dir` e (se houver DB) o bloco `database`.
- Para um path ausente no Profile, `workflow-dev` infere a stack pelo manifesto
  (`go.mod` → `expert-backend-go`; `package.json` com `react` → `expert-frontend-react`)
  e avisa que inferiu — o Profile é sempre a fonte autoritativa quando presente.
- Regras de **segurança do produto** (locks nomeados, gating de endpoints sensíveis,
  CORS/gateway, rate-limit, auth de storage) continuam no `CLAUDE.md` do projeto —
  o plugin carrega apenas os princípios agnósticos correspondentes.
- Fatos de conexão de banco (nomes de profile stage/prod, dialeto, secret store,
  sinal visual de produção) também ficam no `CLAUDE.md`/Project Profile — o
  `expert-database` é agnóstico ao dialeto (Postgres como referência).

## Extensibilidade

O naming por stack (`expert-backend-go`, `expert-frontend-react`, ...) já deixa o
caminho aberto para novas skills expert conforme surgir necessidade real em algum
projeto consumidor — por exemplo `expert-backend-node`, `expert-frontend-vue`, ou
`expert-database-<outro dialeto>`. Essas skills não existem hoje (YAGNI); são criadas
quando um projeto real exigir, seguindo o mesmo padrão: processo e disciplina
transferível no plugin, fatos concretos no `CLAUDE.md` do projeto.

## Licença

MIT — veja [LICENSE](./LICENSE).
