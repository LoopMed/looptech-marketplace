# Loop de Autonomia / Self-Correction (ReAct) + Trava de Segurança

Bloco embutido em todo prompt de subagente de investigação, desenvolvimento ou debug
despachado pelo `workflow-dev`.

## O bloco a colar no prompt do subagente

```markdown
# INSTRUÇÕES DE AUTONOMIA E REPROCESSAMENTO
Você tem autonomia para executar e reexecutar ferramentas em loop até atingir o
Objetivo Final e seu Critério de Parada explícito.

## Processo iterativo (por tentativa):
1. PENSAMENTO: analise o estado atual e decida o próximo passo (e por que a tentativa
   anterior falhou / o que falta).
2. AÇÃO: execute a ferramenta adequada.
3. OBSERVAÇÃO: analise o resultado retornado.
4. VALIDAÇÃO: o Critério de Sucesso foi atingido? Se sim, finalize e monte o relatório de
   retorno. Se não, ajuste a estratégia e reinicie o ciclo.

## Restrições (trava de segurança):
- Máximo de 5 iterações por subtarefa.
- Ao atingir o limite sem sucesso, PARE e reporte ao agente principal: o motivo do erro,
  o que foi tentado (todas as iterações) e o estado final — nunca "trave em loop infinito".
```

## O ciclo, explicado

- **PENSAMENTO** — antes de qualquer ação, o subagente articula o estado atual e a causa
  provável de qualquer falha anterior. Nunca repete uma ação idêntica sem hipótese nova.
- **AÇÃO** — executa exatamente uma ferramenta/comando por iteração, alinhado ao pensamento
  que a precedeu.
- **OBSERVAÇÃO** — lê o resultado bruto retornado (saída de comando, erro, dado) antes de
  concluir qualquer coisa sobre ele.
- **VALIDAÇÃO** — compara a observação contra o Critério de Sucesso/Parada, de forma
  explícita. Só avança para o relatório final quando a comparação é positiva.

## Trava de segurança — máximo 5 iterações

Nenhuma subtarefa pode iterar indefinidamente. Ao atingir a 5ª tentativa sem satisfazer o
Critério de Sucesso, o subagente **para** e monta um relatório de falha (não um relatório de
sucesso disfarçado) contendo:

1. **Motivo do erro** — a causa-raiz mais provável, com evidência.
2. **O que foi tentado** — todas as iterações, resumidas em ordem (não o rastro bruto —
   isso fica isolado no subagente, ver `subagent-handoff.md`).
3. **Estado final** — em que ponto exato o sistema/código/dado ficou.

Esse relatório de falha segue o mesmo template de retorno de `subagent-handoff.md`
(`## O que foi feito` / `## Evidências / Resultados` / `## Próximos Passos`), com os
"Próximos Passos" apontando a decisão que cabe ao agente principal (ex.: revisar a
abordagem, escalar para o operador humano, ajustar o Objetivo Final).

## Critério de Parada é lógico e binário

O Critério de Sucesso/Parada usado na etapa de VALIDAÇÃO nunca é subjetivo ou aberto
("tente até conseguir", "até ficar bom"). Ele é sempre uma condição verificável
mecanicamente — por exemplo: "o JSON de resposta tem as chaves `data`, `valor` e `status`,
e nenhuma delas é nula". Um critério que não pode ser respondido com sim/não não é um
critério válido para este loop — volte para `success-criteria.md` e reescreva-o antes de
despachar o subagente.
