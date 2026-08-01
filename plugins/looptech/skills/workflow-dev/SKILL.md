---
name: workflow-dev
description: Use ao iniciar QUALQUER tarefa de desenvolvimento (feature, bugfix, hotfix, refactor) em um projeto que declara um Project Profile no CLAUDE.md. Orquestra o ciclo completo — discover → spec+plan → env → implementar → review → lint/tests → PR — dimensionado por lane (S/M/L), delegando toda análise/código a subagentes com handoff rico e loop de autonomia. Detecta a stack de cada sub-projeto e despacha as skills expert corretas (expert-backend-go, expert-backend-python, expert-frontend-react, expert-frontend-pwa, expert-frontend-web, expert-database). NÃO use para projetos sem Project Profile.
---

# Workflow Dev — Orquestrador Agnóstico de Desenvolvimento

## Overview

Ciclo completo de desenvolvimento para qualquer projeto que declare um **Project Profile**
no seu `CLAUDE.md`: **discover → brainstorm → spec+plan → preparar ambiente → implementar →
review → lint+tests → PR**. O processo é o mesmo para qualquer stack; o que muda — paths,
comandos, branches, conexões de banco — vem **inteiramente** do Profile do projeto. Esta
skill carrega **processo e disciplina**, nunca fatos concretos de um produto específico.

**Announce at start:** "Estou usando a skill workflow-dev para guiar esta tarefa."

**Escopo:** aplica-se **somente** a sub-projetos mapeados no Project Profile do `CLAUDE.md`.
Se a tarefa mira um diretório fora do Profile, ou o projeto não declara Profile algum, **pare**
e diga ao usuário que esta skill não cobre o caso — o sub-projeto segue seu próprio processo
ad hoc (documentação local, se houver).

**Princípios centrais:**
- Toda tarefa parte de uma branch base atualizada, vive em ambiente isolado (worktree ou
  equivalente) **dentro do sub-projeto que toca**, sai com testes e entra via PR revisado.
- Specs/plans vivem onde a **Regra de Destino** manda (ver abaixo) — **nunca** dentro do
  código do sub-projeto. Se o projeto tem gestor de memória, é no vault; senão, em `.specs/`.
- **A cerimônia é dimensionada pela lane** (ver `references/lanes.md`). Tarefas pequenas
  correm enxutas; features grandes recebem o pipeline completo.
- **Review antes do commit é obrigatório em toda lane** — nunca é pulado, só encadeado.

---

## Fase 0 — Resolver o Project Profile · main

**Primeira ação, sempre.** Leia o `CLAUDE.md` do projeto (e do sub-projeto, se houver um
próprio) e monte o mapa `path → stack → comandos → convenções` antes de tocar em qualquer
código. O contrato completo do Project Profile — o que ele precisa declarar, o formato de
referência, a resolução de UX por área e a inferência de stack por manifesto quando um path
não está mapeado — está em [`references/project-profile.md`](references/project-profile.md).

- **Path ausente no Profile:** infira a stack pelo manifesto do diretório (arquivo de
  dependências/build da linguagem, framework declarado no manifesto de pacote, etc.) e
  **avise explicitamente** que a stack foi inferida, não declarada — nunca trate a inferência
  como certeza silenciosa.
- **Sem Profile algum:** pare a execução desta skill e informe ao usuário que o projeto
  precisa declarar um Project Profile antes de usar este workflow.
- Todo comando de teste/lint/build/integração citado em qualquer fase adiante **vem do
  Profile** — nunca hardcode um comando aqui.
- **Resolva também o destino de spec/memória**: o `CLAUDE.md` declara um bloco `memory:`?
  Se sim, o projeto tem gestor de memória — spec/plano vão para o vault e a memória da tarefa
  é obrigatória (carregue `memory-graph:memory-vault`). Se não, vale o `specs_dir` do Profile
  ou o fallback `.specs/`. Ver a **Regra de Destino** na Fase 3.

---

## DELEGATION MANDATE — o Orquestrador é Puro Orquestrador

Regra dura, acima de qualquer lane: **o agente principal nunca faz análise de código,
implementação, ajuste ou ajuste pós-review por conta própria — tudo é delegado a subagente.**

| Ação | Quem faz |
|------|----------|
| Análise/investigação de código, mapeamento, blast radius | **subagente** (handoff rico + loop de autonomia) |
| Implementação de qualquer task (inclusive lane S) | **subagente** dev |
| Ajustes pós-review (aplicar CHANGES-REQUESTED) | **subagente** dev |
| Code review de todo diff | **subagente** reviewer |
| **Edição trivial ≤ 100 caracteres** (typo, bump de versão, uma linha de config) | orquestrador pode fazer direto |
| Coordenação: ler o Project Profile, classificar a lane, colar contexto, despachar, coletar síntese | orquestrador |
| Rodar comandos de verificação/git (test/lint/build, commit, push, abrir PR) | orquestrador executa o comando; **a análise da falha e o fix vão para subagente** |

**Impacto na lane S:** não existe mais "orquestrador implementa direto". Mesmo na lane S, a
implementação vai para **um subagente dev** (recebendo o diagnóstico que o orquestrador já
tem via handoff rico) e o review continua obrigatório antes do commit. O orquestrador só
"mete a mão" em código quando a mudança inteira cabe em **≤ 100 caracteres**.

**Loop de ajuste pós-review:** review devolve `CHANGES-REQUESTED` → **novo subagente dev**
aplica os ajustes (recebendo o diff atual + os pontos do review como Estado Atual) →
re-review → commit. O orquestrador nunca aplica o fix ele mesmo.

---

## Lanes — Dimensionar o Processo pela Tarefa (PRIMEIRA DECISÃO)

Classifique a tarefa **antes de qualquer outra coisa**. Critérios completos de S/M/L, o que
cada lane pula ou exige, e a regra de "quando em dúvida, promova" estão em
[`references/lanes.md`](references/lanes.md).

---

## Model Assignment

O orquestrador (este agente principal) roda sempre no **modelo default da sessão** — não
troca de modelo no meio da tarefa. Subagentes recebem um `model` explícito:

| Trabalho | Roda em | Modelo |
|----------|---------|--------|
| Discover, brainstorm, preparação de ambiente, lint+tests, abertura de PR, coordenação | **agente principal** | default da sessão |
| Spec+Plan (combinado, lanes M/L) | **subagente** | modelo de maior raciocínio disponível (ex.: opus) |
| Implementação de código por task (toda lane, inclusive S) | **subagente(s)** | modelo intermediário (ex.: sonnet) |
| Code review (toda lane) | **subagente** | modelo intermediário (ex.: sonnet) |

---

## Golden Rule para Todo Subagente — Handoff Rico + Loop de Autonomia

Subagentes começam com contexto vazio. Todo minuto que um subagente gasta redescobrindo o
que o orquestrador já sabia é desperdício puro — e é o que faz o subagente parecer lento.

- **Cole, não aponte.** Todo despacho de subagente segue o protocolo completo de
  [`references/subagent-handoff.md`](references/subagent-handoff.md): Objetivo Final (com
  critério de sucesso binário), Estado Atual (referências exatas, coladas, não apontadas),
  Variáveis Críticas, e o conhecimento expert de arquitetura relevante aos arquivos tocados.
- **Reviewers recebem o diff inline.** Rode o diff no agente principal e cole a saída no
  prompt de review, junto com o "Done when" da task. O reviewer não deve precisar explorar.
- **Subagentes de desenvolvimento e debug** embutem também o loop de autonomia descrito em
  [`references/autonomy-react-loop.md`](references/autonomy-react-loop.md) — o ciclo
  Pensamento → Ação → Observação → Validação, com trava de segurança de iterações e a
  obrigação de reportar (nunca travar em loop infinito) quando o limite é atingido sem
  sucesso.
- **Nunca instrua um subagente a "carregar a skill e ler os arquivos de plano"** quando o
  orquestrador já pode colar o conteúdo relevante. Só peça a subagentes dev que leiam os
  arquivos-fonte que eles próprios vão editar.
- **Declare o formato de retorno** explicitamente — todo subagente encerra com o template de
  três seções de `subagent-handoff.md` (O que foi feito / Evidências-Resultados / Próximos
  Passos).

---

## Critérios de Sucesso Obrigatórios

Nenhuma spec, plano ou handoff de subagente começa sem critério de sucesso **testável e
binário** — nunca "tente até funcionar". A disciplina completa (o que exigir na entrada de
spec/plan, como cada task herda um "Done when" verificável, e como o critério de sucesso vira
a condição de parada do loop de autonomia) está em
[`references/success-criteria.md`](references/success-criteria.md).

---

## Fases do Ciclo

Todos os paths, comandos e convenções de branch citados abaixo vêm do Project Profile
resolvido na Fase 0 — nada aqui é hardcoded.

### Fase 1 — Discover Sub-projetos & Atualizar da Branch Base · main

Identifique, via Project Profile, qual(is) sub-projeto(s) a tarefa toca; carregue a skill
expert de stack de cada um (ver "Dispatch de Skill Expert" abaixo). Atualize cada sub-projeto
afetado a partir da branch base declarada no Profile (`vcs.base`), tratando cada um como seu
próprio repositório se assim estiver configurado. Salvo pedido explícito do usuário para
partir de outra branch, sempre atualize e ramifique a partir da base declarada (ou da base de
hotfix, se aplicável).

### Fase 2 — Brainstorm · main

Rodado no agente principal — precisa do contexto completo da conversa. Objetivos: entender
escopo e impacto, identificar quais sub-projetos/camadas são tocados, resolver ambiguidades
com o usuário, e **classificar a lane** (S/M/L) e o tipo de branch, conforme as convenções de
prefixo declaradas no Profile. Use exploração direcionada (busca/leitura de código) ou uma
ferramenta de mapeamento de codebase quando a área for genuinamente desconhecida e o mapa já
existir — nunca construa esse mapa no meio de uma tarefa. A lane S pula direto para
preparação de ambiente + execução enxuta.

### Fase 3 — Spec + Plan (combinado) · subagente · modelo de maior raciocínio · (lanes M/L)

Delegue spec **e** plano a **um único subagente** — as duas fases compartilham todo o
contexto, então separá-las em dois agentes só duplica o custo de partida fria. Rode em
paralelo com a preparação de ambiente (o ambiente não depende da spec). A skill de
planejamento em si (a que produz spec/design/tasks) é a que o **projeto** declarar — esta
skill não embute o conteúdo dela, só referencia seu uso e cola o resultado nos handoffs
seguintes.

Saída esperada: spec (com requisitos rastreáveis), design (só quando há decisões de
arquitetura genuínas) e uma lista de tasks atômicas — cada uma com What, Where (paths
exatos), Depends on, Reuses, ID de requisito, Done when, Tests e mensagem de commit; tasks
independentes marcadas para paralelismo. Grave conforme a **Regra de Destino** abaixo.

#### Regra de Destino — vault se houver, `.specs/` se não

Resolva **nesta ordem**, uma única vez por tarefa, e diga ao usuário qual caminho valeu:

1. **O `CLAUDE.md` declara um bloco `memory:`** (gestor de memória instalado) → grave **no
   vault**, em `<vault>/70-Specs/<feature>/`, **sempre pelo `obsidian` CLI**. Carregue
   `memory-graph:memory-vault` antes de escrever.
2. **Sem bloco `memory:`, mas o Profile declara `specs_dir`** → use `specs_dir` como está.
3. **Nenhum dos dois** → `.specs/<feature>/` na raiz, e **avise** que o projeto ganharia um
   vault rodando `memory-graph:memory-vault-setup`.

> `.specs/` é **fallback**, não o padrão. Não crie `.specs/` num projeto que já tem vault —
> memória em dois lugares diverge, e a divergência não avisa.

#### Formato canônico de nome — obrigatório nos três caminhos

**`<Tipo> - <Título da feature>`**, com `<Tipo>` ∈ `Spec` · `Design` · `Tasks` · `Plan`:

```
<destino>/<feature>/
├── Spec - <Título da feature>.md
├── Design - <Título da feature>.md
├── Tasks - <Título da feature>.md
└── Plan - <Título da feature>.md
```

- O título é o da **feature**, não o H1 do documento — assim o tripé da mesma feature fica
  junto na busca e no grafo.
- Documento extra da mesma feature leva qualificador entre parênteses:
  `Tasks - <Feature> (backend)`, `Plan - <Feature> (rollback)`, `Design - <Feature> (contexto)`.
- Outro tipo de documento segue o mesmo padrão `<Tipo> - <Título da feature>`.
- **Nunca** `spec.md` / `design.md` / `tasks.md`: dezenas de arquivos com o mesmo nome tornam
  o wikilink ambíguo e o grafo ilegível.
- **Sanitize o nome** contra `\ / : * ? " < > |` e `# ^ [ ]`. Ao gravar via `obsidian` CLI,
  lembre que ele **só bloqueia `\ / :`** — os outros ele aceita e grava um nome inválido —
  e que **retorna exit code 0 mesmo falhando**: confira o stdout e releia a nota.

### Preparação de Ambiente — Isolamento por Sub-projeto · main · (paralelo à Fase 3)

Crie um ambiente isolado (worktree ou equivalente da stack) dentro de cada sub-projeto
afetado, nomeado pela feature, ramificando da branch base já atualizada (ou da base de
hotfix). Siga as convenções de prefixo/branch/PR-target declaradas em `vcs` no Profile.
Reaproveite cache de dependências sempre que possível (não reinstale às cegas quando o lock
de dependências não mudou) — o comando exato de instalação vem do Profile de cada stack.

### Fase 6-S — Executar, Lane S · subagente dev + 1 subagente review

Mesmo na lane S, a implementação vai para **um subagente dev** — não para o orquestrador (ver
Delegation Mandate). O orquestrador cola o diagnóstico/plano enxuto (uma frase de escopo,
arquivos a tocar, abordagem, comando de verificação) no handoff do subagente. Ciclo
red→green→refactor dentro do ambiente isolado, tocando só os arquivos listados. Rode o gate
de teste/lint declarado no Profile. **Um subagente de review é obrigatório antes do commit**,
recebendo o diff final + os critérios "Done when" + as regras aplicáveis coladas. Só comite
após APPROVE, então avance para a Fase 8.

### Fase 6 — Executar, Lanes M/L: Dev + Review Encadeado · subagentes

Tasks marcadas como independentes rodam **concorrentemente**, um subagente por task; tasks
dependentes rodam em ordem de dependência. **Encadeie as reviews — nunca serialize
dev → review → dev.** A review de uma task só bloqueia **seu próprio commit**, não o
desenvolvimento da próxima task:

```
dev T1 ──► review T1 ──► commit T1
        └─(enquanto isso)─► dev T2 ──► review T2 ──► commit T2
```

Todo prompt de dev e de review segue o protocolo de `subagent-handoff.md` (contexto colado,
não apontado) e, para dev/debug, embute o loop de `autonomy-react-loop.md`. **Nunca comite
uma task antes que seu subagente de review aprove** — a review por task é tão obrigatória
quanto os testes.

### Fase 7 — Lint + Testes da Feature · main, direto

Depois que **todas** as tasks estiverem commitadas, rode o gate completo diretamente via
comando no agente principal — não spawne subagente para isso. **Reproduza localmente cada
check que o CI do projeto roda**, na **mesma forma** que o CI roda (não só "rodar o linter",
mas rodar exatamente como o pipeline declarado no Profile/CI do projeto roda, incluindo
variantes como "somente linhas novas" quando o CI usar essa forma — os comandos exatos e os
gotchas de CI vêm de `ci_gotchas` no Profile). Não abra o PR antes de todo comando do gate
passar; reporte falhas literalmente, nunca declare sucesso sem colar a saída do comando.

### Fase 8 — Disciplina de Commit & PR · main

Commits específicos (nunca add cego de tudo), sem pular hooks de verificação, sem forçar
push. Antes de abrir ou atualizar qualquer PR, sincronize a branch com a branch base mais
recente e reexecute os testes se houver conflito. Abra um PR por sub-projeto afetado (cada um
seguindo seu próprio target de PR conforme `vcs` no Profile), com resumo do que mudou, plano
de teste (comandos do Profile) e checklist de que a branch foi sincronizada e nenhum segredo
foi commitado. Antes de pedir review humano, revise o PR como um todo (todas as tasks
implementadas e testadas, changeset coerente, descrição fiel). Após aprovação e merge, limpe
o ambiente isolado (remova worktree/branch).

---

## Fechamento — Registrar o que foi aprendido · main

Se o projeto declara um bloco `memory:`, a tarefa **não está concluída** sem registro:

- Decisão de arquitetura, gotcha que custou tempo, incidente resolvido ou contrato verificado
  ao vivo → nota no vault (`20-Projetos/<Produto>/` ou `30-Referencia/`), via `obsidian` CLI.
- **Sempre** uma linha no log do mês (`90-Log/AAAA-MM.md`) com o que foi feito e o link da nota.
- Nada disso é opcional, e nada disso é escrito com `Write`/`Edit` — só pelo CLI.

O protocolo completo (taxonomia, frontmatter, validação pós-gravação) está em
`memory-graph:memory-vault`. Sem bloco `memory:`, pule esta fase.

---

## Dispatch de Skill Expert por Sub-projeto

Para cada sub-projeto tocado, carregue a skill expert de **stack** que o Project Profile
declarar para aquele path (ou que a inferência por manifesto indicar, com aviso).

- **Persistência/banco de dados:** se a tarefa toca a camada de dados de qualquer stack,
  carregue **também** a skill expert de banco de dados — ela cobre disciplina de query,
  fluxo de execução (preflight → discovery → execução), gate de produção e a regra de
  migration por existência, tudo resolvido pelos fatos concretos do bloco `database` do
  Profile.
- **Frontend — dois eixos que compõem:** carregue a skill de **engenharia** da stack
  declarada (arquitetura de componentes, tipagem, testes, segurança em princípio) **mais** a
  skill de **UX/UI/interação** resolvida por área — case cada path tocado contra as
  sobrescritas de UX declaradas no Profile (glob mais específico vence) e caia no default
  declarado quando nenhuma sobrescrita casar. Se a tarefa cruza mais de uma área (ex.: toca
  tanto a área com orientação mobile-first quanto a área com orientação web-first), carregue
  **ambas** as skills de UX e **sinalize a fronteira** explicitamente no handoff do
  subagente — não escolha uma arbitrariamente.
- Skills expert carregam **princípios e disciplina transferíveis** (nunca nomes concretos de
  função, tabela ou produto) — os fatos concretos de segurança/negócio do projeto continuam
  no `CLAUDE.md` e devem ser colados no handoff junto com o conhecimento expert.

---

## Quick Reference

```
FASE 0: resolver Project Profile — path → stack → comandos → convenções (nunca hardcode)
LANE PRIMEIRO: S (poucos arquivos, escopo trivial) | M (feature clara) | L (multi-componente/ambíguo)
MANDATO: orquestrador NUNCA implementa/analisa/ajusta código — só edição trivial ≤100 chars

1. Discover      → main · Project Profile resolvido · skill(s) expert carregada(s) · sync com a base
2. Brainstorm    → main · classificar lane · resolver ambiguidade
3. Spec+Plan     → subagente (modelo de maior raciocínio, lanes M/L)
   DESTINO       → bloco memory:? vault/70-Specs/<feature>/ · senão specs_dir · senão .specs/
   NOME          → "<Tipo> - <Título da feature>"  (Spec|Design|Tasks|Plan) — nunca spec.md
Env prep         → main · ambiente isolado por sub-projeto · paralelo à Fase 3
6-S (lane S)     → subagente dev (TDD) → subagente review no diff final → commit
6 (lanes M/L)    → subagentes dev em paralelo quando independentes · reviews ENCADEADAS
7. Lint + tests  → main, direto — reproduzir CADA check de CI na forma exata do Profile
8. PR            → main · sincronizar com a base primeiro · PR por sub-projeto · review final do PR
Cleanup          → remover ambiente isolado + branch, por sub-projeto
Fechamento       → se há bloco memory:: nota no vault + linha em 90-Log/AAAA-MM.md (via CLI)
```

---

## Red Flags — PARE imediatamente se ver isto

- Rodar este workflow para um sub-projeto fora do que o Project Profile declara
- Orquestrador implementando, analisando ou ajustando código com mais de 100 caracteres —
  inclusive na lane S, inclusive em ajuste pós-review
- Pular a Fase 0 — nenhum Project Profile resolvido antes de começar a tocar código
- Não classificar a lane antes de começar (tratar tudo como pipeline completo por padrão)
- Escrever código antes de Spec+Plan estar pronto (lanes M/L) — ou escrever spec/plano para
  uma tarefa de lane S
- Escrever spec/plano dentro do código de um sub-projeto em vez do destino resolvido na Fase 3
- Criar `.specs/` num projeto que **já tem** bloco `memory:` — memória em dois lugares diverge
- Nomear documento de planejamento como `spec.md`/`design.md`/`tasks.md` em vez de
  `<Tipo> - <Título da feature>`
- Gravar no vault com `Write`/`Edit` em vez do `obsidian` CLI, ou confiar no exit code do
  `create` sem conferir o stdout
- Encerrar a tarefa sem nota + linha no log quando o projeto declara bloco `memory:`
- Um prompt de subagente que diz "carregue a skill e leia os arquivos de plano" em vez de
  colar o contexto
- Um prompt de review sem o diff colado inline
- Serializar dev → review → dev quando as tasks são independentes — encadear
- Comitar qualquer código antes do subagente de review aprovar (toda lane)
- Reinstalar dependências às cegas em um ambiente isolado quando o lock não mudou
- Spawnar um subagente só para rodar lint/testes (a Fase 7 roda no agente principal)
- Abrir/atualizar um PR sem sincronizar com a branch base primeiro
- Abrir um PR antes de lint + testes estarem verdes na forma exata que o CI do projeto usa
- Rodar o linter/gate na forma "repositório inteiro" quando o CI do projeto usa uma forma
  restrita (ex.: só linhas novas) — comparar contra a forma errada mascara um bloqueador real
- Comitar pulando hooks de verificação, empurrar direto para a branch base, ou adicionar
  arquivos às cegas
- Abrir PR com o prefixo/target de branch errado para o tipo de mudança declarado no Profile
- Hardcodar aqui qualquer comando, path, nome de conexão ou regra de negócio que deveria vir
  do Project Profile ou de uma skill expert
