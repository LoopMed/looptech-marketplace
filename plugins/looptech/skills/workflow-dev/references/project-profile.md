# Project Profile — o Contrato que o `CLAUDE.md` Preenche

`workflow-dev` lê este bloco no `CLAUDE.md` de cada projeto — é a fonte determinística de
sub-projetos, stack, comandos, convenções de VCS e (se houver) banco de dados. Elimina o
"adivinhar": o orquestrador nunca infere um comando ou um path por tentativa quando o
Profile já os declara.

## Regra de ouro

O plugin carrega **processo e disciplina transferível**; o `CLAUDE.md` do projeto carrega os
**fatos concretos** — paths reais, comandos exatos que espelham o CI, nomes de conexão,
convenções de branch. O Project Profile é o ponto único de tradução entre os dois.

## Formato de referência (YAML)

```yaml
## Project Profile (workflow-dev)
subprojects:
  - { path: <sub>/,             stack: expert-backend-go }
  - path: <sub>/
    stack: expert-frontend-react            # eixo de engenharia
    ux_default: expert-frontend-pwa         # área principal = mobile-first
    ux_overrides:                            # eixo de UX, por path (mais específico vence)
      - { match: "src/**/admin/**", ux: expert-frontend-web }   # área admin = web-first
  - { path: <sub>/,             stack: expert-backend-go }
  - path: <sub>/
    stack: expert-frontend-react
    ux_default: expert-frontend-web          # produto web-first / dark-first
  # fora do workflow (ad hoc): sub-projetos de infraestrutura, scripts, serviços de terceiros
vcs:       { base: <base>, pr_target: <base>, prefixes: [feature, fix, hotfix], hotfix_base: <main> }
specs_dir: <destino>/<feature>/    # ver bloco memory: — .specs/ só como fallback
commands:
  expert-backend-go:
    test:  "<comando de teste do Profile>"
    integ: "<comando de teste de integração do Profile>"
    lint:  "<comando de lint do Profile>"   # forma que espelha o CI; DEVE reportar "0 issues"
    build: "<comando de build do Profile>"
  expert-frontend-react:
    test:  "<comando de teste do Profile>"
    lint:  "<comando de lint do Profile>"
    types: "<comando de checagem de tipos do Profile>"
    build: "<comando de build do Profile>"
  expert-frontend-vue:
    test:  "<comando de teste do Profile>"
    lint:  "<comando de lint do Profile>"
    types: "<comando de checagem de tipos do Profile>"
    build: "<comando de build do Profile>"
database:
  connections: { stage: <nome-da-conexão-stage>, prod: <nome-da-conexão-prod> }
  dialect: <dialeto>
  discovery: { tables: "<comando de listar tabelas>", schema: "<comando de listar schema>", indexes: "<comando de listar índices>" }
  migrations_table: <tabela-de-tracking-de-migration>
ci_gotchas: |
  - <peculiaridade do lint/CI do projeto, se houver>
  - <o que o CI não roda e precisa ser reproduzido local>
  - <mapeamento branch → ambiente de deploy>
```

> O formato de referência é YAML; um projeto pode declarar o Profile em tabela Markdown
> equivalente. O que importa é o `workflow-dev` conseguir resolver: sub-projetos, stack por
> path, comandos por stack, convenção de branch/PR, `specs_dir` e (se houver) os blocos
> `database` e `memory`.

## Bloco `memory` — onde vivem memória, spec e plano

Opcional, mas quando presente **manda mais que `specs_dir`**. Declarado no `CLAUDE.md` da raiz
pela skill `memory-graph:memory-vault-setup`:

```yaml
memory:
  vault: <NomeDoVault>            # nome registrado no Obsidian (não o caminho)
  path: <pasta/do/vault>          # relativo à raiz do projeto
  produtos: [<Produto>, ...]      # subpastas de 20-Projetos/
  specs_dir: 70-Specs/<feature>/  # dentro do vault
  pii: permitida | proibida | perguntar
```

### Regra de Destino (resolvida uma vez, na Fase 0)

| Estado | Onde grava spec/plano | Memória da tarefa |
|---|---|---|
| Bloco `memory:` presente | `<vault>/70-Specs/<feature>/`, via `obsidian` CLI | **obrigatória** — nota + linha no log |
| Sem `memory:`, com `specs_dir` | o `specs_dir` declarado | opcional |
| Nenhum dos dois | `.specs/<feature>/` (**fallback**) | — · sugira `memory-graph:memory-vault-setup` |

Em qualquer um dos três, o nome do documento é **`<Tipo> - <Título da feature>`**
(`Spec` · `Design` · `Tasks` · `Plan`), com o título vindo da **feature**. Nunca `spec.md`.

> Projeto com bloco `memory:` **não** deve ganhar um `.specs/` — memória em dois lugares
> diverge, e a divergência não avisa.

## Detecção de stack (o "identificar a linguagem")

O Profile é **autoritativo** — resolve stack por `path → stack`. Para um path **ausente** no
Profile, `workflow-dev` **infere pelo manifesto** do sub-projeto (ex.: presença de um
manifesto de módulo Go implica `expert-backend-go`; um `pyproject.toml`/`requirements.txt`
implica `expert-backend-python`; um manifesto de pacote JS com dependência de React implica
`expert-frontend-react`; com dependência de Vue implica `expert-frontend-vue`) e **avisa
explicitamente** que a stack foi inferida, não declarada. Isso entrega detecção automática
sem abrir mão do determinismo — a inferência é sempre visível, nunca silenciosa.

## Resolução de UX (por área, não por sub-projeto)

UX/UI/interação é um **eixo separado** da engenharia. Ao tocar arquivos de um frontend,
`workflow-dev`:

1. Casa cada path tocado contra as entradas de `ux_overrides` (glob **mais específico**
   vence quando há mais de um match).
2. Cai em `ux_default` quando nenhum override casa.
3. Carrega a skill de UX resultante **além** da skill de engenharia (`expert-frontend-react`
   ou equivalente) — as duas compõem, nunca se substituem.
4. Se a task cruza áreas (ex.: toca uma área com `ux_override` e também a área do
   `ux_default`), carrega **ambas** as skills de UX e sinaliza a fronteira explicitamente no
   handoff do subagente (ver `subagent-handoff.md`) — o subagente precisa saber que está
   operando em duas orientações de UX diferentes dentro da mesma task.

A skill de engenharia despachada é a do Profile (`expert-frontend-react` **ou**
`expert-frontend-vue`); a de UX (`pwa`/`web`) compõe com qualquer uma das duas.

## O que o Profile precisa resolver, no mínimo

- **Sub-projetos** — todo path relevante do repositório e sua stack.
- **Stack por path** — engenharia (`expert-backend-*`, `expert-frontend-*`) e, quando
  aplicável, UX (`ux_default`/`ux_overrides`).
- **Comandos por stack** — test/lint/types/build, na forma exata que o CI usa.
- **Convenção de branch/PR** — branch base, alvo de PR, prefixos, base de hotfix.
- **`specs_dir`** — onde ficam spec/design/tasks, **quando não há bloco `memory:`**.
- **Bloco `memory`** (se houver) — vault, produtos e política de PII; vence o `specs_dir` e
  torna o registro de memória obrigatório ao fim da tarefa.
- **Bloco `database`** (se houver banco) — nomes de conexão, dialeto, comandos de discovery,
  tabela de tracking de migration. Ver `expert-database` para o fluxo que consome esse bloco.
