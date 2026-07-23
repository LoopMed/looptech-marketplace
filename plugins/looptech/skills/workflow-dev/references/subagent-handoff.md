# Handoff de Subagente — Entrada Rica + Isolamento + Retorno Estruturado

Referenciado por **todo** template de subagente em `workflow-dev`. Nenhum subagente é
despachado sem seguir este protocolo.

## Princípio

O orquestrador nunca despacha um subagente "para descobrir". O orquestrador já sabe o
suficiente do Project Profile, da skill expert carregada e da investigação prévia para
**colar** esse conhecimento diretamente no prompt do subagente. O subagente **recebe →
planeja → executa**; ele não gasta iterações remontando contexto que o orquestrador já tinha.

## Entrada — o orquestrador SEMPRE cola os quatro blocos

### 1. Objetivo Final
O que construir/investigar/corrigir, incluindo a **validação de negócio / critérios de
sucesso** — a condição binária de "pronto" (ver `success-criteria.md`). Nunca despachar um
subagente com um objetivo vago ("melhora isso aí") sem a condição de parada explícita.

### 2. Estado Atual
Referências **exatas** — arquivos, dados, trechos de código **colados no prompt**, não
apontados por caminho para o subagente "ir ler depois". Se o orquestrador já leu o arquivo
relevante, o conteúdo relevante vai no prompt. Isso inclui:
- Caminhos absolutos dos arquivos/diretórios envolvidos.
- Trechos de código/config/dados já coletados.
- Resultado de comandos já executados (test/lint/build, queries, etc.).

> **Nunca "leia o §X de um documento grande".** Colar o trecho exato de que o subagente
> precisa é o protocolo; mandá-lo abrir uma spec/design de centenas de linhas para extrair
> sua parte força re-leitura — o mesmo documento relido por N subagentes em paralelo — e é
> exatamente o "redescobrir" que este protocolo existe para matar. Cole o texto-fonte,
> não o ponteiro. Só peça a um subagente dev que abra o **arquivo-fonte que ele próprio vai
> editar**.

### 3. Variáveis Críticas
Parâmetros de negócio relevantes à tarefa — regras não-negociáveis, valores/limites que não
podem ser inferidos errado, convenções do projeto que mudam o resultado se ignoradas.

### 4. Conhecimento expert da arquitetura
As 5–15 linhas da skill expert (stack + Project Profile) que impõem arquitetura,
desacoplamento e convenções nos arquivos tocados. O subagente **respeita a arquitetura do
projeto** porque já recebeu a regra — não porque foi descobrir sozinho lendo o repositório
inteiro.

## Granularidade e fan-out — 1 subagente por unidade independente

Cada subagente recebe **somente o que é da sua responsabilidade**, com escopo definido na
etapa de spec/plan. A decomposição correta das tasks é o que torna o handoff enxuto — uma
task bem-scopada cabe inteira, inline, no prompt.

- **Uma unidade independente = um subagente.** Arquivos/tasks sem dependência direta (não
  compartilham arquivo nem estado) são despachados **em paralelo**, um subagente por unidade.
- **Nunca empacote N arquivos independentes num único subagente** — isso serializa dentro
  dele o que deveria correr em paralelo (ex.: 5 arquivos editados em sequência por 1 agente,
  quando 5 agentes fariam em paralelo no tempo de 1).
- **Só agrupe no mesmo subagente** tasks genuinamente acopladas (mesmo arquivo, ou uma
  depende do resultado da outra).
- **Primeiro prompt completo.** Faça o recon (grep de paths, edge cases, estrutura) **antes**
  de despachar, e coloque tudo no primeiro prompt — evita rodadas de follow-up, cada uma
  pagando cold-start de novo.

## Isolamento de contexto

Todo ruído da execução — buscas exploratórias, falhas de leitura, tentativa-e-erro,
iterações do loop de autonomia — fica **apenas** na janela de contexto do subagente. Nada
disso consome a janela do agente principal. Ao terminar, o subagente devolve **só o
resultado sintetizado**, nunca o rastro bruto de exploração.

## Checkpoint de progresso — o subagente é dono do próprio contexto

Todo subagente de **tarefa longa** (múltiplos passos, edição de vários pontos, investigação
extensa) mantém o **seu próprio arquivo de checkpoint** em memória/scratch — não depende da
janela de contexto sobreviver inteira até o fim.

- **O que registrar:** o que já foi feito, o estado atual, e o **próximo passo concreto** —
  atualizado a cada marco relevante, não só no fim.
- **Por quê:** se o contexto do subagente estourar no meio da tarefa, ele **retoma a partir
  do checkpoint** e continua até finalizar — sabe exatamente onde parou e o que falta, sem
  recomeçar do zero nem devolver trabalho pela metade.
- **Onde:** um path de scratch/memória próprio do subagente (não o do orquestrador); o
  subagente cita esse path no retorno para rastreabilidade.
- **Condição de encerramento:** o subagente só se dá por concluído quando o **critério de
  sucesso** (ver `success-criteria.md`) é atingido — o checkpoint é a garantia de que uma
  tarefa longa chega ao fim mesmo cruzando limites de contexto.

## Retorno estruturado (obrigatório)

Todo subagente encerra sua resposta com este template Markdown exato — três seções, nesta
ordem, sem variação de título:

```markdown
## O que foi feito
<rastro auditável da investigação/execução>

## Evidências / Resultados
<dados brutos ou pedaços de código validados>

## Próximos Passos
<o que o agente principal precisa fazer com isso>
```

- **O que foi feito** — resumo do trabalho realizado, em ordem, auditável.
- **Evidências / Resultados** — a prova concreta (saída de comando, trecho de código,
  contagem de linhas, diff) que sustenta a conclusão. Nunca uma afirmação sem evidência.
- **Próximos Passos** — a ação que o agente principal (ou o próximo subagente) precisa tomar
  a partir daqui.

## Red flag

Se um subagente está **"descobrindo"** algo que já era sabido pelo orquestrador — relendo um
arquivo que o orquestrador já tinha aberto, redescobrindo uma convenção que a skill expert já
declarava — o contexto entregue **estava incompleto**. A correção é no **prompt** do próximo
despacho, nunca uma cobrança ao subagente. Um subagente que investiga do zero é sintoma de
handoff malfeito, não de subagente preguiçoso.
