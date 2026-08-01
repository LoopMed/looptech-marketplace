---
name: memory-vault-setup
description: Use para configurar a memória de um projeto pela primeira vez, ou quando o usuário pedir "configurar memória", "criar vault", "migrar memórias", "/memory-graph:setup". Valida se a skill e o CLI do Obsidian estão instalados, detecta ou cria o vault do projeto com o dev, grava o bloco `memory:` e o protocolo nos CLAUDE.md/AGENTS.md, encontra memória legada espalhada pelo repositório, e conduz a migração completa com validação e verificação de paridade antes de oferecer apagar ou manter como backup. NÃO use para o uso diário da memória (isso é `memory-graph:memory-vault`) nem quando o bloco `memory:` já existe e o vault já está populado.
---

# memory-vault-setup — Onboarding e Migração da Memória

## Overview

Leva um projeto de "memória espalhada / inexistente" até "um vault Obsidian é a única fonte,
e todo agente é obrigado a usá-lo". Cinco passos, cada um no ritmo
**DETECTA → REPORTA → OFERECE (com confirmação)**.

**Announce at start:** "Estou usando a skill memory-vault-setup para configurar a memória deste projeto."

**Princípios centrais:**
- **Nada é apagado sem backup e sem confirmação.** Migrar e apagar são decisões separadas.
- **Idempotente:** rodar de novo num projeto configurado só valida e reporta.
- **Verificar, nunca presumir.** O `obsidian` CLI retorna exit code 0 mesmo falhando — toda
  gravação é conferida.
- Agnóstico de produto: nome do vault, produtos e pastas vêm do que o usuário confirmar.

---

## Passo 1 — Pré-requisitos (skill + CLI do Obsidian)

**DETECTA:**

```bash
which obsidian                      # CLI no PATH?
obsidian vaults                     # app rodando? lista os vaults registrados
```

E confirme que as skills `obsidian:obsidian-cli` e `obsidian:obsidian-markdown` aparecem na
lista de skills disponíveis.

**REPORTA** o que falta, com precisão — os três problemas têm causas diferentes:

| Sintoma | Causa | O que instruir |
|---|---|---|
| `which obsidian` vazio | CLI não instalado | Obsidian → Settings → **CLI** → habilitar e instalar. Docs: https://help.obsidian.md/cli |
| `obsidian vaults` → *unable to find Obsidian* | App fechado | Abrir o Obsidian e manter aberto — o CLI conversa com o app |
| skills `obsidian:*` ausentes | Plugin não instalado | `/plugin marketplace add obsidianmd/obsidian-claude-code` + `/plugin install obsidian` (confirme o marketplace correto com o usuário) |

**OFERECE:** instrua o usuário a resolver e **pare aqui** até `obsidian vaults` responder.
Nenhum passo seguinte funciona sem isso. Não tente contornar com escrita direta em disco.

---

## Passo 2 — Vault do projeto

**DETECTA**, nesta ordem:

1. Bloco `memory:` no `CLAUDE.md` do projeto → o vault já está declarado.
2. Diretório contendo `.obsidian/` na raiz do projeto ou um nível abaixo → vault existe mas
   não está declarado.
3. `obsidian vaults` → algum nome bate com o projeto?

**REPORTA:** um dos três estados — *configurado* / *vault existe mas não declarado* /
*não existe*.

**OFERECE** — se não existir, **crie junto com o dev**, perguntando:
- **Nome do vault** (sugira `<Projeto>Memory`) e **onde** fica (sugira `<raiz>/<Nome>/`).
- **Quais são os produtos/sub-projetos** — viram subpastas de `20-Projetos/`.
- **PII pode ser registrada?** A resposta vira regra escrita no bloco `memory:`. Se o usuário
  não souber, registre `pii: perguntar` — melhor que assumir.

Peça para o usuário **abrir a pasta como vault no Obsidian** (o CLI só enxerga vault
registrado) e confirme com `obsidian vaults` antes de seguir.

Então crie a estrutura — **sempre via CLI**, validando cada gravação:

```
00-Sistema/     LEIA PRIMEIRO — Protocolo de Memória · Taxonomia e Convenções
                Receitas do Obsidian CLI · Inbox · Templates/
10-Mapas/       MOC — Índice Geral + um MOC por produto
20-Projetos/    uma pasta por produto confirmado
30-Referencia/  40-Decisoes/  50-Feedback/  70-Specs/  90-Log/  99-Arquivo/
```

Templates mínimos em `00-Sistema/Templates/`: `T - Projeto`, `T - Referência`,
`T - Decisão (ADR)`, `T - Feedback`, `T - Incidente`, `T - Log Mensal`. Configure a pasta de
templates em `.obsidian/templates.json` (`{"folder": "00-Sistema/Templates"}`) e confirme com
`obsidian templates`.

O conteúdo de `LEIA PRIMEIRO`, `Taxonomia` e `Receitas` é o protocolo da skill
`memory-graph:memory-vault` — gere-os a partir dela, não invente um protocolo novo.

### Gravar o bloco `memory:` e forçar o uso

No `CLAUDE.md` da raiz:

```yaml
memory:
  vault: <NomeDoVault>
  path: <pasta/do/vault>
  produtos: [<Produto>, ...]
  specs_dir: 70-Specs/<feature>/
  pii: permitida|proibida|perguntar
```

E propague o **bloco de protocolo** para:
- o `CLAUDE.md` da raiz **e** o de cada sub-projeto;
- **todo `AGENTS.md`** — Codex, Gemini e Copilot leem esse arquivo e **não** o `CLAUDE.md`;
  sem isso o protocolo fica invisível para eles;
- o `CLAUDE.md` do próprio vault (regra nº 1: nunca editar o vault com `Write`/`Edit`).

O bloco deve mandar: carregar `memory-graph:memory-vault`, buscar antes de implementar, gravar
ao terminar + linha no `90-Log/`, e listar o proibido (escrita direta, memória fora do vault,
omitir `vault=`, valor de segredo).

---

## Passo 3 — Memória legada no projeto

**DETECTA** — varra o repositório inteiro (exceto `node_modules`, `.venv`, worktrees):

| Onde | O que costuma ser |
|---|---|
| `.claude/memory/` | `MEMORY.md` (índice), `ACTIVITY-LOG.md`, arquivos de tópico |
| `~/.claude/projects/<slug>/memory/` | auto-memória do harness (`<slug>` = caminho absoluto com `/`→`-`) |
| `**/memory.md`, `NOTES.md`, `ACTIVITY-LOG.md` | memória solta de sub-projeto |
| `.specs/`, `docs/superpowers/`, `.agent-os/` | specs e planos |
| `**/.superpowers/` | artefatos de sessão |

> **Varra os sub-repos, não só a raiz.** `<repo>/docs/superpowers/` e `<repo>/.specs/` costumam
> ter conteúdo **diferente** do da raiz. Comparar por hash de conteúdo é a única forma segura
> de saber o que já está no vault.

**REPORTA** uma tabela: origem · nº de arquivos · tamanho · já está no vault?

**OFERECE:** pergunte se deseja migrar — e **o quê**. Ofereça em grupos, não tudo ou nada:
núcleo de memória / operacional / specs e planos. Se houver `MEMORY.md` gigante ou
`ACTIVITY-LOG.md`, avise que serão fatiados por mês.

---

## Passo 4 — Migração

Só rode com o "sim" do Passo 3.

### 4.1 Backup primeiro

```bash
mkdir -p .archive
tar czf .archive/memoria-pre-migracao-AAAA-MM-DD.tar.gz <origens...>
```

Backup em local **durável** — nunca no diretório temporário da sessão, que evapora.

> **Antes de apagar qualquer coisa, inventarie os arquivos NÃO-markdown.** Pastas de spec
> costumam esconder script SQL, shell de cutover, `.env` e `.secrets*` que ninguém migrou.
> Perder isso é irreversível.

### 4.2 Rotear e nomear

- **Prefixo do arquivo** define a pasta: `project_*`→`20-Projetos/<Produto>/`,
  `reference_*`→`30-Referencia/`, `feedback_*`/`user_*`→`50-Feedback/`.
- **Produto** vem do **slug do arquivo**, nunca do corpo — palavras soltas no texto
  ("vercel", "kong") contaminam o roteamento e mandam a nota para o produto errado.
- **Título:** use o primeiro `# H1` do corpo. Se for genérico (== nome do arquivo), derive da
  pasta da feature. **Nunca** corte a descrição no primeiro ponto — abreviação e nome de
  arquivo quebram a frase.
- **Planejamento** (`spec`/`design`/`tasks`/`plan`) usa o formato canônico
  **`<Tipo> - <Título da feature>`**, com o título vindo da **feature**, não do H1 — assim o
  tripé da mesma feature fica junto. Extra da mesma feature: qualificador entre parênteses.
- **Sanitize contra os 9 caracteres** (`\ / : * ? " < > |` + `# ^ [ ]`), não contra os 3 que
  o CLI bloqueia.

### 4.3 Preservar o grafo de links

Coloque em `aliases` **todas** as variantes do nome antigo:

```
slug_com_underscore · slug-com-hifen · sem_prefixo · sem-prefixo · caminho/antigo
```

O acervo antigo costuma linkar com hífen **e** com underscore. Aliasar só uma das formas
quebra metade dos `[[links]]` — e o `read file=` do CLI **não** resolve alias, então valide
com `search`.

### 4.4 Gravar, validando cada nota

Use `create ... silent overwrite` — **nunca** `rename` em lote (reescreve backlinks no vault
inteiro, >90s por arquivo). Depois de cada gravação, cheque o stdout: exit code 0 não
significa sucesso.

Fatie log cronológico grande em `90-Log/AAAA-MM.md` + um `Log — Índice`.

### 4.5 Verificar — não presuma

```bash
# paridade: nº de .md na origem == nº no vault?
# frontmatter completo (titulo/tipo/status/atualizado) em 100% das notas?
# links quebrados: liste [[...]] fora de code block que não resolvem por nome, path ou alias
# nomes com caractere proibido: 0
# órfãs: nota sem entrada nenhuma = faltou linkar num MOC
```

Só declare a migração concluída depois de rodar essas cinco checagens e reportar os números.

### 4.6 Só então: apagar ou manter?

**Pergunte.** Ofereça três opções e explique a consequência de cada uma:

| Opção | Consequência |
|---|---|
| Manter como backup | Nada quebra, mas agentes podem gravar no lugar antigo por engano |
| Apagar, deixando redirect | Recomendado — um `README.md`/`MEMORY.md` curto apontando para o vault impede recriação |
| Apagar tudo | Mais limpo, sem rede de proteção além do tarball |

> **Se os arquivos forem git-tracked**, apagar é mudança de repositório: reporte o número de
> deleções pendentes por repo e branch, e **não commite nem faça push** sem pedido explícito.
> Worktrees são checkouts transitórios — não os toque.

### 4.7 Consertar o que ficou apontando para o vazio

Depois de apagar, varra por referências mortas em **skills, `CLAUDE.md`, `AGENTS.md` e
`README.md`**. Skill que ainda manda "salvar plano em `docs/superpowers/plans/`" vai falhar na
próxima execução. Esse é o passo mais esquecido da migração.

---

## Passo 5 — Índice semântico e resumo

Aponte o MCP `memory-graph` para o vault e rode a indexação inicial:

```bash
MEMORY_GRAPH_DIR="<caminho/do/vault>" uv run --directory <plugin> python -m memory_graph reindex
```

Avise que o **primeiro** reindex baixa o modelo de embedding (~130MB, uma vez) e que os tools
de memória só aparecem **depois de reiniciar a sessão**.

Encerre com resumo binário:

```
✅ Pré-requisitos — CLI ok, Obsidian aberto, skills carregadas
✅ Vault — <Nome> criado com N pastas e M templates
✅ Protocolo — bloco memory: + protocolo em X CLAUDE.md e Y AGENTS.md
✅ Migração — N notas migradas, 0 links quebrados, frontmatter 100%
⚠️ Legado — mantido como backup em .archive/ (usuário optou por não apagar)
⚠️ Pendente — N deleções não commitadas em <repo> (<branch>)

Próximo passo: reinicie a sessão para o MCP memory-graph aparecer.
```

Grave a própria migração como nota no vault + linha no `90-Log/` — dogfooding do protocolo.

---

## Quick Reference

```
1. Pré-requisitos → which obsidian + obsidian vaults + skills obsidian:* → PARE se faltar
2. Vault          → detectar (bloco memory: / .obsidian/ / obsidian vaults)
                  → criar COM o dev (nome, produtos, PII) → estrutura + templates
                  → bloco memory: no CLAUDE.md + protocolo em TODO CLAUDE.md e AGENTS.md
3. Legado         → varrer raiz E sub-repos → tabela por origem → perguntar o que migrar
4. Migração       → backup durável → rotear por slug → aliases (hífen E underscore)
                  → create+validar → 5 checagens → perguntar apagar/manter → consertar refs
5. Índice         → MEMORY_GRAPH_DIR=<vault> reindex → resumo ✅/⚠️ → reiniciar sessão
```

---

## Red Flags — PARE imediatamente se ver isto

- Seguir para o Passo 2 sem `obsidian vaults` responder
- Criar o vault sem perguntar nome, produtos e política de PII ao dev
- Escrever no vault com `Write`/`Edit` em vez do CLI
- Migrar sem backup, ou com backup no diretório temporário da sessão
- Apagar origem antes de rodar as 5 verificações do 4.5
- Apagar sem perguntar, ou commitar/pushar deleção git-tracked sem pedido explícito
- Apagar diretório de spec sem inventariar os arquivos não-markdown (`.sql`, `.sh`, `.env`)
- Rotear produto pelo corpo do texto em vez do slug do arquivo
- Aliasar só uma variante do nome antigo
- Confiar no exit code do `create`
- Deixar `AGENTS.md` sem o protocolo — outros agentes não leem `CLAUDE.md`
- Declarar a migração concluída sem reportar os números das verificações
