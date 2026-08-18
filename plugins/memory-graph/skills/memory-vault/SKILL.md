---
name: memory-vault
description: Use SEMPRE que a tarefa envolver memória do projeto — ler, buscar, criar ou atualizar nota, decisão, gotcha, incidente, spec, plano ou log — em qualquer projeto cujo `CLAUDE.md` ou `AGENTS.md` declare um bloco `memory:` apontando para um vault Obsidian. Cobre o protocolo diário (buscar antes de implementar, gravar ao terminar), a taxonomia de pastas e frontmatter, o formato canônico de nome, a política de segredo, e as armadilhas do `obsidian` CLI que fazem gravação falhar em silêncio. NÃO use para configurar o vault pela primeira vez nem para migrar memória antiga (isso é `memory-graph:memory-vault-setup`).
---

# memory-vault — Protocolo de Memória em Vault Obsidian

## Overview

Toda memória do projeto vive em **um único vault Obsidian**, declarado no bloco `memory:` do
Project Profile (`CLAUDE.md` / `AGENTS.md`). Escrita passa **sempre** pelo `obsidian` CLI;
leitura pode usar o CLI ou a busca semântica do `memory-graph` (MCP), que indexa o mesmo vault.

**Announce at start:** "Estou usando a skill memory-vault para consultar/gravar a memória."

**Pré-requisitos** (se faltar algum, pare e rode `memory-graph:memory-vault-setup`):
- `obsidian` CLI no PATH e **Obsidian aberto** — o CLI conversa com o app rodando.
- Bloco `memory:` no `CLAUDE.md` **ou** `AGENTS.md` do projeto com o nome do vault.
- Skill `obsidian:obsidian-cli` disponível (e `obsidian:obsidian-markdown` para criar nota).

**Princípios centrais:**
- **Buscar antes de implementar, gravar ao terminar.** Trabalho não registrado é trabalho que
  será refeito.
- **Escrita só pelo CLI.** `Write`/`Edit` direto no arquivo do vault corrompe índice e
  backlinks em silêncio.
- **O CLI não protege você.** Ele mente no exit code e aceita nomes inválidos. Sanitize e
  valide — ver § Armadilhas.
- Esta skill carrega **processo**; os fatos concretos (nome do vault, pastas, produtos) vêm do
  bloco `memory:` do Project Profile do projeto.

---

## Fase 0 — Resolver o bloco `memory:`

Leia o `CLAUDE.md` **e** o `AGENTS.md` do projeto e extraia o bloco `memory:` (se os dois
existirem e divergirem, pare e pergunte qual vence):

```yaml
memory:
  vault: <NomeDoVault>          # nome registrado no Obsidian, não o caminho
  path: <pasta/do/vault>        # relativo à raiz do projeto
  produtos: [<Produto>, ...]    # subpastas de 20-Projetos/
  specs_dir: 70-Specs/<feature>/
```

Se não houver bloco `memory:`, **pare** e diga ao usuário que o vault não está configurado —
oferecer `memory-graph:memory-vault-setup`. Nunca invente um nome de vault.

> **Sempre passe `vault="<NomeDoVault>"` como primeiro parâmetro de todo comando.** Sem isso o
> CLI escreve no vault que estiver em foco — e o registro vai para o lugar errado, em silêncio.

---

## Fase 1 — RECALL (antes de qualquer implementação)

```bash
obsidian vault="<V>" read file="LEIA PRIMEIRO — Protocolo de Memória"   # 1x por sessão
obsidian vault="<V>" search:context query="<tema>" limit=10
obsidian vault="<V>" read file="<MOC da área>"
obsidian vault="<V>" backlinks file="<nota relevante>"
```

Cheque também a pasta de feedback/preferências antes de decidir processo, e o mês corrente do
log para saber o que aconteceu recentemente.

Quando o MCP `memory-graph` estiver ativo, `memory_search` dá recall **semântico** (acha por
significado, não por palavra) sobre o mesmo vault — use os dois: semântico para descobrir,
`search:context` para confirmar o trecho exato.

---

## Fase 2 — CAPTURA (durante a tarefa)

Achou algo não-óbvio e não quer perder o fio:

```bash
obsidian vault="<V>" append path="00-Sistema/Inbox.md" \
  content="- [ ] AAAA-MM-DD — <fato bruto a triar>"
```

---

## Fase 3 — GRAVAÇÃO (ao terminar — não é opcional)

```bash
# nota nova, a partir de template
obsidian vault="<V>" create path="20-Projetos/<Produto>/<Tipo> - <Título>.md" \
  template="T - Projeto" silent

# ou atualizar a existente
obsidian vault="<V>" append file="<nota>" content="\n## AAAA-MM-DD — <o que mudou>\n<detalhe>"
obsidian vault="<V>" property:set name="atualizado" value="AAAA-MM-DD" type="date" file="<nota>"

# SEMPRE: uma linha no log do mês
obsidian vault="<V>" append path="90-Log/AAAA-MM.md" \
  content="\n## AAAA-MM-DD — <título curto>\n<o que foi feito / decidido / resultado> → [[<nota>]]"
```

**Valide depois de gravar** — obrigatório, ver § Armadilhas.

---

## O que vira nota (e o que não vira)

| Vira nota | Não vira nota |
|---|---|
| Decisão de arquitetura/produto e **o porquê** | O que o código já diz sozinho |
| Gotcha que custou tempo para descobrir | Histórico de git |
| Contrato de API / topologia verificada ao vivo | Conteúdo já escrito num `AGENTS.md` |
| Incidente: sintoma → causa raiz → fix → estado | Detalhe válido só nesta conversa |
| Preferência / regra de trabalho do usuário | Rascunho não confirmado |
| Número de negócio apurado | Cópia de spec que já vive em `70-Specs/` |

**Regra de ouro:** se um agente que chegar daqui a 3 meses sem contexto precisaria disso para
não repetir o erro → vira nota.

---

## Taxonomia

```
<vault>/
├── 00-Sistema/     protocolo, taxonomia, receitas, Inbox, Templates/
├── 10-Mapas/       MOCs — porta de entrada por produto e área
├── 20-Projetos/    <Produto>/ — memória viva: feature, incidente, estado
├── 30-Referencia/  fatos duráveis: contratos, topologias, gotchas de plataforma
├── 40-Decisoes/    ADRs
├── 50-Feedback/    preferências e regras de trabalho do usuário
├── 60-Operacional/ áreas de negócio (quando houver)
├── 70-Specs/       specs e planos por feature
├── 90-Log/         diário cronológico por mês: AAAA-MM.md
└── 99-Arquivo/     notas superadas (nunca deletar, arquivar)
```

**`20-Projetos` vs `30-Referencia`:** projeto tem prazo de validade ("estamos fazendo X", "o
bug foi corrigido na v1.49"); referência é verdade até a plataforma mudar ("o CI builda como
arquivo único"). Na dúvida, **20-Projetos** — promover depois é fácil.

### Frontmatter obrigatório

```yaml
---
titulo: "<título humano>"
tipo: projeto|referencia|decisao|feedback|operacional|spec|log|moc|sistema
produto: [<Produto>]
area: [<área>]
status: em-prod|ativo|em-andamento|pendente|arquivado
criado: AAAA-MM-DD
atualizado: AAAA-MM-DD        # atualize SEMPRE que editar
origem: <de onde veio, se migrado>
aliases: [<nome antigo>, <slug antigo>]
tags: [tipo/<t>, produto/<p>, area/<a>, status/<s>]
---
```

Sem `tipo` + `produto` + `atualizado`, a nota é invisível para a busca dos outros agentes.

### Corpo

Feche **toda** nota com `## Relacionadas` e ao menos um link para o MOC do produto — é assim
que ela entra no mapa em vez de virar órfã. Linke agressivamente com `[[...]]`; link para nota
inexistente é bem-vindo: marca lacuna, não é erro.

---

## Formato canônico de nome

Documento de planejamento: **`<Tipo> - <Título da feature>`**, `<Tipo>` ∈
`Spec` · `Design` · `Tasks` · `Plan`.

```
70-Specs/<feature>/
├── Spec - <Título da feature>.md
├── Design - <Título da feature>.md
├── Tasks - <Título da feature>.md
└── Plan - <Título da feature>.md
```

O título é o da **feature**, não o H1 do documento — assim o tripé da mesma feature fica junto
no grafo e na busca. Documento extra da mesma feature leva qualificador entre parênteses:
`Tasks - <Feature> (backend)`, `Plan - <Feature> (rollback)`, `Design - <Feature> (contexto)`.

Nunca `spec.md` / `tasks.md` / `design.md`: dezenas de arquivos com o mesmo nome tornam o
wikilink ambíguo e o grafo ilegível.

Notas comuns (não-planejamento) usam título humano direto, sem prefixo de tipo.

---

## 🔐 Segredo nunca entra na memória

**Proibido gravar o VALOR** de senha, token, API key, secret, connection string com
credencial, conteúdo de `.env`, chave privada, certificado ou cookie de sessão — e a saída de
qualquer comando que contenha um deles. Registre a **referência**:

| ❌ Nunca | ✅ Sempre |
|---|---|
| `TOKEN=EAAG…` | "o token vive em `<arquivo>` como `<VAR>`" |
| `postgres://user:senha@host/db` | "conecta via `service=<nome>`; credencial no secret store" |

**Exceção:** o usuário autorizar **explicitamente, naquela tarefa**. Aí marque a nota:

```markdown
> ✅ **Exceção autorizada (AAAA-MM-DD):** <quem> autorizou manter <o quê> nesta nota.
> **Não redija** ao aplicar a política 🔐.
```

Sem essa marca, o próximo agente aplica a política e redige de novo.

**Antes de decidir sobre PII**, cheque o bloco `memory:` do projeto — projetos diferentes têm
regras diferentes. Se o projeto não declarar nada, **pergunte** em vez de assumir. Onde PII for
permitida, a trava costuma ser na **saída** (relatório externo, deck, PR público), não na
gravação.

**Antes de afirmar que algo "vazou"**, confirme o estado real do sync:

```bash
obsidian vault="<V>" sync:status      # "Sync is not set up for this vault" = local
```

`core-plugins.json` com `"sync": true` significa apenas que o plugin está habilitado por
padrão — **não** que há um remoto configurado. Não alarme o usuário com base nisso.

---

## Armadilhas do CLI (todas verificadas)

| Sintoma | Causa / correção |
|---|---|
| Gravou e não achou depois | Faltou `vault="<V>"` — foi para o vault errado |
| `create` disse *Error* mas o script seguiu | **O CLI retorna exit code 0 mesmo falhando.** O erro sai só no stdout — valide o stdout ou releia a nota |
| Nome com `< > * ? " \|` entrou no vault | O CLI **só bloqueia `\ / :`**; os outros ele **aceita e grava**. Sanitize você |
| Nota com `:` no nome "sumiu" | `\ / :` são bloqueados — erro no stdout, exit 0, nada gravado |
| `search query="08:00"` → *Operator not recognized* | `:` é operador na busca. Troque por espaço |
| `read file="<slug antigo>"` dá *not found* | `file=` **não resolve alias** — só nome de arquivo. Use `search` e depois `read path=` |
| Nota some das buscas por property | Frontmatter escrito à mão com indentação errada — use `property:set` |
| Nota abriu e roubou o foco | Faltou a flag `silent` |
| Conteúdo saiu numa linha só | `content` usa `\n` literal, não quebra real |
| Comando não responde / *unable to find Obsidian* | Obsidian fechado — o CLI fala com o app rodando |
| `rename` travando em lote | `rename` reescreve backlinks no vault inteiro (>90s/arquivo). Para lote: `create` no caminho novo + remover o antigo, com o nome velho em `aliases` |

### Sanitização — obrigatória antes de todo `create`/`rename`

```python
import re
INVALID = re.compile(r'[\\/:*?"<>|#^\[\]]')     # 9 chars, não os 3 que o CLI bloqueia
nome = INVALID.sub("-", titulo).strip(" .-")
```

`#`, `^`, `[`, `]` entram na lista: o CLI aceita, mas quebram wikilink e âncora
(`[[nota#seção]]`, `[[nota^bloco]]`).

### Validação — obrigatória depois de todo `create`

```bash
saida=$(obsidian vault="<V>" create path="$P" content="$C" silent)
case "$saida" in Error*) echo "FALHOU: $saida"; exit 1;; esac
obsidian vault="<V>" read path="$P" | head -3      # confirma que existe
```

---

## Quick Reference

```
0. Resolver     → ler bloco memory: do CLAUDE.md / AGENTS.md → vault, produtos, specs_dir
1. RECALL       → search:context + MOC da área + backlinks (e memory_search se MCP ativo)
2. CAPTURA      → append no 00-Sistema/Inbox.md
3. GRAVAÇÃO     → create (template) OU append + property:set atualizado
4. SEMPRE       → linha em 90-Log/AAAA-MM.md
5. VALIDAR      → checar stdout + reler a nota (exit code mente)
```

---

## Red Flags — PARE imediatamente se ver isto

- Escrever em arquivo do vault com `Write`/`Edit`/`sed` em vez do `obsidian` CLI
- Omitir `vault="<V>"` em qualquer comando
- Criar arquivo de memória **fora** do vault (`.claude/memory/`, `memory.md`, `NOTES.md`,
  `ACTIVITY-LOG.md`) — se encontrar um, migre e apague
- Confiar no exit code do `create` sem checar o stdout
- Montar nome de arquivo sem sanitizar os 9 caracteres
- Gravar valor de segredo sem autorização explícita **daquela tarefa**
- Afirmar que houve vazamento sem rodar `sync:status`
- Fechar a tarefa sem a linha no `90-Log/`
- Usar `spec.md`/`tasks.md`/`design.md` em vez de `<Tipo> - <Título da feature>`
- Inventar nome de vault, produto ou pasta que não está no bloco `memory:`
