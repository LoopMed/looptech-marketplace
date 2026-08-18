# Critérios de Sucesso Obrigatórios

Imposto na **entrada** de toda spec/plan e propagado a todo handoff de subagente
(`subagent-handoff.md`). Nenhuma fase do workflow avança sem isso definido primeiro.

## Regra

- **Nenhuma spec/plan inicia sem critérios de sucesso testáveis.** Antes de escrever
  requisitos ou desenhar uma abordagem, o que será validado — e como saber que terminou —
  precisa estar explícito. Critérios são escritos **antes** da implementação, nunca
  retroativamente para justificar o que já foi feito.
- **Cada task herda um critério de "Done when" verificável.** Toda task atômica do plano
  carrega sua própria condição de conclusão, derivada do critério de sucesso da feature —
  não uma reafirmação vaga do objetivo geral.
- **O critério de sucesso é a condição de parada dos loops ReAct dos subagentes.** A etapa
  de VALIDAÇÃO do ciclo Pensamento→Ação→Observação→Validação (`autonomy-react-loop.md`)
  compara diretamente contra este critério — não existe critério de parada "paralelo"
  inventado pelo subagente em tempo de execução.

## O que torna um critério válido

Um critério de sucesso é testável quando pode ser respondido de forma binária (sim/não) por
qualquer pessoa ou processo, sem precisar de julgamento subjetivo:

- **Válido:** "o endpoint retorna 200 com o campo `id` populado e a linha existe na tabela
  correspondente após o commit."
- **Válido:** "todos os testes do comando de teste do Profile passam, sem `skip`."
- **Inválido:** "a funcionalidade está funcionando bem."
- **Inválido:** "o código ficou mais limpo."

## Onde isso se conecta

- **Entrada de spec/plan** — a fase de planejamento (delegada à skill de planejamento do
  projeto) não é aceita como completa sem essa seção preenchida.
- **Handoff de subagente** — todo Objetivo Final colado num prompt de subagente
  (`subagent-handoff.md`) inclui a validação/critério de sucesso correspondente.
- **Loop de autonomia** — todo Critério de Parada usado em `autonomy-react-loop.md` deriva
  diretamente daqui; não é reescrito ad hoc pelo subagente.
- **Revisão de correção antes de commit** — o subagente `review` confere o diff contra o
  critério de sucesso declarado, não contra uma impressão geral de qualidade.
- **Revisão de segurança antes de commit** — o subagente `security` confere o mesmo diff
  contra `security-review.md` (dano à empresa). `SECURE` sem evidência de checagem é
  inválido; `ISSUES-FOUND` bloqueia o commit.
