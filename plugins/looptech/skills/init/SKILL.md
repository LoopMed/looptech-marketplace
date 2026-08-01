---
name: init
description: Use quando o plugin looptech acabou de ser instalado num projeto e nada foi configurado ainda, ou quando o usuário pede explicitamente "/looptech:init", "configurar o looptech", "inicializar o looptech", "setup do looptech", "onboarding de projeto", "configurar banco/serena/memória do looptech". Guia o projeto do zero ao pronto: Project Profile no CLAUDE.md, conexão de banco, MCP de navegação de código (Serena, opcional), memória em vault Obsidian (recomendado) e validação de runtimes. NÃO use para tarefas de desenvolvimento do dia a dia (isso é looptech:workflow-dev) nem quando o Project Profile já existe e está completo — nesse caso não há nada a inicializar.
---

# looptech:init — Setup Guiado do Projeto

## Overview

Setup **sob demanda**, rodado uma vez (ou revalidado) por projeto: leva um projeto recém-instalado
do plugin looptech do zero ao pronto para o `looptech:workflow-dev` funcionar. Cobre 6 passos —
Project Profile, banco, Serena, memory-graph, runtimes, resumo — cada um seguindo o mesmo
ritmo: **DETECTA → REPORTA → OFERECE corrigir (com confirmação)**.

**Announce at start:** "Estou usando a skill looptech:init para configurar este projeto."

**Princípios centrais:**
- **Nunca grava segredo silenciosamente.** Toda credencial vem do usuário, nunca é inventada.
- **PROD nunca é tocado sem OK humano explícito** — em nenhum dos 6 passos.
- **Idempotente:** rodar de novo num projeto já configurado só valida e reporta, não sobrescreve
  sem perguntar.
- Esta skill é **agnóstica de produto** — todo fato concreto (nomes de conexão, paths, comandos)
  vem do que for detectado ou do que o usuário confirmar, nunca de um exemplo hardcoded.
- Passos 3 e 4 são **opcionais**: ofereça, explique o ganho, mas siga em frente sem eles se o
  usuário recusar ou se o pré-requisito não estiver disponível (`uv` para ambos; `obsidian`
  CLI + app aberto para o Passo 4).

---

## Passo 1 — Project Profile

O `looptech:workflow-dev` lê o **Project Profile** do `CLAUDE.md` do projeto para saber
sub-projetos, stacks, comandos e convenções de branch. Sem ele, o workflow não roda.

**DETECTA:** leia `./CLAUDE.md`. Se já existir uma seção `## Project Profile`, valide sua
estrutura (sub-projetos com `path`+`stack`, `vcs`, `specs_dir`, `commands` por stack) contra o
que existe de fato no repositório — aponte divergências (path que não existe mais, stack que
mudou, comando que não roda). Se não existir, o projeto precisa de um Profile novo.

**REPORTA:** liste os sub-projetos que você detectou por manifesto (ex.: `go.mod` → Go,
`pyproject.toml`/`requirements.txt` → Python, `package.json` com `react` na dependência →
React) e a stack inferida para cada um. Para cada sub-projeto de frontend, identifique também
o eixo de UX (mobile-first vs. web-first) por área do código — ex.: áreas de admin/operador
tendem a web-first, o resto tende a mobile-first — e proponha `ux_default` + `ux_overrides`
por glob.

**OFERECE:** monte o bloco YAML abaixo com o usuário, confirmando cada campo antes de escrever
no `CLAUDE.md` — em especial os comandos de `test`/`lint`/`build`, que devem **espelhar
exatamente o que o CI do projeto roda** (não um comando genérico da stack) e a branch
base/target de PR:

```yaml
## Project Profile (looptech:workflow-dev)
subprojects:
  - { path: <dir>/, stack: expert-backend-go }        # detectar por manifesto: go.mod→go, pyproject→python
  - path: <dir>/                                        # package.json c/ react → react
    stack: expert-frontend-react
    ux_default: expert-frontend-pwa                     # mobile-first; use expert-frontend-web p/ web/admin
    ux_overrides: [ { match: "src/**/admin/**", ux: expert-frontend-web } ]
vcs: { base: develop, pr_target: develop, prefixes: [feature, fix, hotfix], hotfix_base: main }
specs_dir: .specs/<feature>/                            # fallback; o bloco memory: abaixo vence
commands:
  expert-backend-go:   { test: "<cmd>", lint: "<cmd CI>", build: "<cmd>" }
  expert-frontend-react:{ test: "<cmd>", lint: "<cmd>", types: "<cmd>", build: "<cmd>" }
database: { connections: { stage: <nome>, prod: <nome> }, dialect: postgres, discovery: { tables: "\\dt", schema: "\\d <t>", indexes: "\\di <t>" }, migrations_table: schema_migrations }
memory: { vault: <NomeDoVault>, path: <pasta>/, produtos: [<Produto>], specs_dir: 70-Specs/<feature>/, pii: perguntar }
```

Os blocos `database:` e `memory:` só são preenchidos de fato nos Passos 2 e 4 — deixe o
placeholder aqui e retorne para completá-los depois. Se o usuário recusar o vault no Passo 4,
**remova** o bloco `memory:` em vez de deixá-lo com placeholder: um `memory:` pela metade faz
o `workflow-dev` mirar um vault que não existe. Só grave no `CLAUDE.md` após confirmação
explícita do usuário sobre o conteúdo final.

---

## Passo 2 — Banco

Siga o fluxo de **preflight/onboarding de conexão** do `looptech:expert-database` (Metade B,
Etapa 0) — esta skill não reimplementa aquele fluxo, só o dispara e cola o resultado no
Project Profile.

**DETECTA:** existe algum profile de conexão já registrado no secret store do dialeto (ex.:
`~/.pgpass` + `~/.pg_service.conf` para Postgres) apontando para os nomes que o Profile vai
declarar? Teste conectividade com um comando inócuo (ex. `conninfo`/`SELECT 1`).

**REPORTA:** se não houver conexão configurada, ou se falhar, explique exatamente o que falta
— nunca avance para descoberta de schema com conexão vermelha.

**OFERECE:**
1. Confirme com o usuário o **dialeto** e os **nomes de conexão** (stage/prod) a declarar.
2. Mostre as **linhas exatas** a acrescentar no secret store do dialeto (ex. entrada de
   `~/.pgpass` no formato `host:port:database:user:senha`, e o bloco correspondente em
   `~/.pg_service.conf`) — **peça as credenciais ao usuário**, nunca as invente ou reutilize de
   outro contexto. **O agente NUNCA escreve no `~/.pgpass`/`~/.pg_service.conf` (ou equivalente)
   por si mesmo — mesmo se o usuário colar a senha no chat e pedir para gravar direto. Você só
   mostra as linhas; quem edita o arquivo de segredo é sempre o usuário.**
3. Depois de o usuário confirmar que gravou as credenciais, teste a conectividade com uma
   leitura inócua no ambiente de **stage** (nunca prod por padrão).
4. Grave o bloco `database:` completo no Project Profile (Passo 1) com os nomes de conexão,
   dialeto e comandos de discovery confirmados.

**PROD:** só testar/configurar a conexão de produção com **validação humana explícita** —
pergunte antes de tocar nela, mesmo para um teste de conectividade.

---

## Passo 3 — Serena (opcional — navegação de codebase)

Serena expõe tools de navegação semântica de código (símbolos, referências, LSP da stack) via
MCP. Opcional: ofereça, mas siga sem ele se recusado ou sem pré-requisito.

**DETECTA:**
- Rode `uv --version` (ou equivalente) para checar se `uv` está disponível — é pré-requisito.
- Monte a lista de **sub-projetos candidatos** a partir do Project Profile (Passo 1): cada
  sub-projeto cuja stack tem um LSP suportado (ex. Go→`gopls`, React/TS→`typescript-language-server`,
  Python→`pyright`/`basedpyright`).

**VALIDA:** para cada candidato, confirme que o diretório existe e tem o manifesto da stack
(`go.mod`, `package.json`, `pyproject.toml`, …) e que o LSP correspondente está disponível ou
pode ser baixado sob demanda. Descarte da lista o que não validar (e diga por quê).

**REPORTA:** se `uv` faltar, informe que Serena depende dele e ofereça o link de instalação
primeiro. Senão, mostre a lista **validada** de sub-projetos candidatos com a stack/LSP de cada.

**PERGUNTA (obrigatório):** **pergunte ao usuário QUAIS sub-projetos validados ele quer
registrar/indexar no Serena** — nunca registre todos por conta própria. Ofereça seleção
múltipla (ex.: "todos", "só backend", "backend + frontend", …).

**OFERECE (com confirmação):** registre **um único** MCP server em modo **multi-projeto** (sem
`--project`, para expor o `activate_project` e permitir navegar todos os escolhidos), **fixado
numa release estável** e com o **dashboard web desligado**:

```
claude mcp add serena -- uvx --from git+https://github.com/oraios/serena@<tag-estável> serena start-mcp-server --context ide-assistant --enable-web-dashboard false
```

- **`@<tag-estável>`**: use a **release mais recente** (veja `github.com/oraios/serena/releases`),
  **nunca o git HEAD** — o HEAD pode vir com bugs de CLI/schema.
- **`--enable-web-dashboard false`**: sem isso o Serena **abre uma aba do navegador a cada
  start** do server (que reinicia a cada conexão) — é chato; desligue.
- Se o usuário escolher **um só** sub-projeto, pode simplificar com `--project "<dir>"`.
- Os sub-projetos escolhidos são **registrados sob demanda** no primeiro `activate_project`
  (não dependa da CLI `serena project index/create`, que é instável).

Avise que:
- O **LSP da stack** é baixado sob demanda na primeira navegação — pode demorar na 1ª vez.
- Os tools novos (e o dashboard desligado) só valem **depois de reiniciar a sessão** do Claude Code.

---

## Passo 4 — Memória em vault Obsidian (recomendado)

Memória do projeto num **vault Obsidian**: escrita pelo `obsidian` CLI, recall semântico pelo
MCP `memory-graph`. É o que faz decisão, gotcha e incidente sobreviverem entre sessões — e o
que o `workflow-dev` consulta para não refazer trabalho já feito.

**DETECTA** — três checagens independentes, não junte:

```bash
which obsidian                 # CLI instalado?
obsidian vaults                # app aberto? lista os vaults registrados
uv --version                   # pré-requisito do MCP (mesmo do Passo 3)
```

E confirme no `CLAUDE.md` se já existe um bloco `memory:`, e no repositório se já existe uma
pasta com `.obsidian/`.

**REPORTA** — cada sintoma tem causa diferente:

| Sintoma | Causa | Instrução |
|---|---|---|
| `which obsidian` vazio | CLI não instalado | Obsidian → Settings → **CLI** → habilitar. https://help.obsidian.md/cli |
| `obsidian vaults` → *unable to find Obsidian* | App fechado | Abrir e manter aberto — o CLI fala com o app |
| skills `obsidian:*` ausentes | Plugin não instalado | Instalar o plugin de skills do Obsidian |
| sem bloco `memory:` | vault não configurado | Passo abaixo |

Avise também que o **primeiro** uso do MCP baixa um modelo local (fastembed, ~130MB), uma
única vez.

**OFERECE**, com confirmação — delegue à skill dedicada, que faz o trabalho completo:

```
Skill("memory-graph:memory-vault-setup")
```

Ela cobre, em ordem: validar CLI e skills → criar o vault **junto com o dev** (nome, produtos,
política de PII) → estrutura de pastas e templates → gravar o bloco `memory:` no `CLAUDE.md` e
o protocolo em **todo** `CLAUDE.md` **e `AGENTS.md`** (outros agentes leem só o `AGENTS.md`) →
varrer memória legada no repositório → perguntar o que migrar → migrar com backup, validação e
verificação de paridade → perguntar apagar ou manter → consertar referências mortas.

Se o usuário recusar o vault, siga sem ele: o `workflow-dev` cai no fallback `.specs/` e o
projeto simplesmente não terá memória entre sessões. Diga isso explicitamente, não deixe
implícito.

Ao final, aponte o índice semântico para o vault e avise que os tools de memória só aparecem
**depois de reiniciar a sessão**.

---

## Passo 5 — Runtimes

Valide, para cada stack declarada no Project Profile (Passo 1), que as ferramentas de linha de
comando necessárias estão instaladas e na versão esperada.

**DETECTA:** para cada stack do Profile, rode o comando de versão da ferramenta correspondente
(ex.: `go version` + `gopls version` para Go; `node --version` + `npm --version` para
Node/React; `python --version` + `uv --version` para Python).

**REPORTA:** tabela simples do que está OK e do que falta, por stack.

**OFERECE:** para cada ferramenta ausente, aponte o comando/link de instalação padrão da
plataforma do usuário — não instale nada sem confirmação.

---

## Passo 6 — Resumo

Encerre com um resumo binário por passo, nunca vago:

```
✅ Project Profile — gravado no CLAUDE.md (N sub-projetos)
✅ Banco — stage conectado, prod pendente de validação humana
⚠️ Serena — não configurado (usuário recusou)
✅ Memória — vault <Nome> criado, protocolo em N CLAUDE.md e M AGENTS.md, legado migrado
⚠️ Runtimes — falta gopls (instale com: <comando>)

Próximos passos:
- Reinicie a sessão do Claude Code para os MCP servers novos (Serena/memory-graph) aparecerem.
- <qualquer pendência levantada acima>
```

Sempre destaque a necessidade de **reiniciar a sessão** se qualquer MCP novo foi adicionado nos
Passos 3/4.

---

## Quick Reference

```
1. Project Profile   → ler CLAUDE.md → detectar sub-projetos/stack/UX → confirmar comandos (=CI) → gravar
2. Banco             → onboarding do expert-database → linhas exatas do secret store → testar stage → gravar database: no Profile
3. Serena (opcional) → checar uv → claude mcp add serena ... --project "<dir>" → LSP sob demanda → reiniciar sessão
4. Memória (vault)   → which obsidian + obsidian vaults + uv → delegar a memory-graph:memory-vault-setup
                       (cria vault COM o dev, grava memory: + protocolo em CLAUDE.md E AGENTS.md, migra legado) → reiniciar sessão
5. Runtimes          → validar ferramenta de cada stack do Profile → apontar instalação do que falta
6. Resumo            → ✅/⚠️ por passo + lembrete de reiniciar sessão
```

---

## Red Flags — PARE imediatamente se ver isto

- Gravar qualquer credencial de banco **diretamente no secret store** (`~/.pgpass` etc.) —
  mesmo que o usuário a tenha colado no chat e peça para gravar direto. O agente só mostra as
  linhas exatas; quem edita o arquivo é sempre o usuário, mesmo se ele pedir para pular esse passo
- Testar ou configurar conexão de **produção** sem validação humana explícita
- Rodar o comando `claude mcp add serena ...` ou criar o vault de memória sem confirmação
- Criar o vault sem perguntar ao dev o nome, os produtos e a política de PII
- Migrar ou apagar memória legada dentro deste skill — isso é `memory-graph:memory-vault-setup`,
  que faz backup, valida e pergunta antes de apagar
- Sobrescrever um `## Project Profile` existente sem mostrar o diff e confirmar
- Instalar uma ferramenta de runtime ausente sem perguntar antes
- Declarar o Passo 6 "tudo pronto" sem ter reportado reiniciar a sessão quando Serena ou
  o vault de memória foi adicionado
- Hardcodar aqui um nome de produto, sub-projeto, tabela ou conexão — tudo é `<placeholder>`
  até o usuário confirmar
