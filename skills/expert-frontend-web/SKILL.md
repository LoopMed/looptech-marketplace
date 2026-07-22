---
name: expert-frontend-web
description: Disciplina de UI/UX/interação orientada a WEB-FIRST / desktop (agnóstica de produto; Design System, tokens e paleta concretos vêm do CLAUDE.md). Layouts densos de informação, uso de ponteiro/hover, atalhos de teclado, seleção múltipla e arraste, navegação lateral/multi-painel, tabelas/grades densas, breakpoints largos e acessibilidade de teclado completa; foco em fluxos de operador/admin (filtros, ações em lote). Carregue (junto com a skill de engenharia da stack) ao tocar áreas de frontend marcadas como web-first no Project Profile (ux_default/ux_overrides). NÃO cobre arquitetura/TS/testes — isso é o eixo de engenharia (ex.: expert-frontend-react).
---

# Expert Frontend Web (UX web-first / desktop)

## Objetivo

Esta skill define a **orientação de UI/UX/interação** para áreas de frontend
classificadas como **web-first** no Project Profile do projeto
(`ux_default` ou `ux_overrides` apontando para `expert-frontend-web`).

Ela é **um eixo, não uma stack**: compõe com a skill de engenharia (ex.:
`expert-frontend-react`), que continua responsável por arquitetura,
TypeScript, testes e segurança de código. Esta skill **não repete** nada
disso — cobre só a camada de interação e layout otimizada para desktop e
uso de ponteiro.

Design System, tokens de cor, paleta, tipografia e componentes concretos
**não** vivem aqui — eles vêm do `CLAUDE.md` do projeto (ou de uma skill de
marca/produto própria). Esta skill entrega os **princípios** de interação
web-first; o projeto entrega os **fatos** visuais.

## Quando carregar

Carregue esta skill junto com a skill de engenharia da stack sempre que a
task tocar um path de frontend resolvido como web-first pelo Project
Profile (`ux_default: expert-frontend-web` ou um `ux_overrides` cujo glob
casa com os arquivos tocados). Se a task cruzar uma área web-first e uma
área mobile-first (`expert-frontend-pwa`), carregue as duas e sinalize a
fronteira no handoff do subagente.

## Princípios

### 1. Web-first / ponteiro

- O layout parte do pressuposto de **mouse/trackpad + teclado** como
  entrada primária, não de toque. Hover é um estado de primeira classe:
  use-o para revelar ações secundárias, previews e affordances que não
  precisam competir por espaço permanente na tela.
- Priorize **atalhos de teclado** para ações frequentes (navegação entre
  itens, confirmar, cancelar, buscar) e documente-os de forma descobrível
  (tooltip, paleta de comandos, cheatsheet).
- Suporte **seleção múltipla** (shift-click, ctrl/cmd-click, "selecionar
  tudo") e **arraste** (drag-and-drop para reordenar, mover entre colunas
  ou fazer upload) onde a tarefa se beneficia disso.
- Estruture a navegação em **layout lateral / multi-painel** (sidebar +
  lista + detalhe, ou colunas paralelas) em vez de empilhar tudo em uma
  única coluna vertical — a largura de tela disponível deve ser usada para
  mostrar mais contexto simultâneo, não para esticar componentes.

### 2. Densidade e escala

- Prefira **tabelas e grades densas** a cards espaçados quando o usuário
  precisa escanear muitos registros de uma vez; densidade de informação é
  uma vantagem em telas grandes, não um defeito a esconder.
- Assuma **breakpoints largos** como caso comum e projete para múltiplas
  colunas de conteúdo lado a lado (lista + filtros + detalhe, ou grade de
  N colunas) em vez de um único fluxo centralizado com margens vazias.
- A interface continua **responsiva** — ela deve degradar com elegância em
  telas menores — mas o ponto de partida do design é a tela grande, não o
  celular. Não sacrifique densidade na tela grande só para simplificar o
  caso móvel.

### 3. Produtividade (fluxos de operador/admin)

- Otimize para usuários que repetem a mesma tarefa muitas vezes por dia:
  **filtros persistentes/salvos**, **ações em lote** (bulk actions sobre
  seleção múltipla), atalhos e navegação por teclado reduzem o custo
  marginal de cada operação.
- Garanta **acessibilidade de teclado completa**: todo elemento
  interativo deve ser alcançável e operável via `Tab`/`Shift+Tab`, `Enter`,
  `Espaço` e setas, com foco visível em cada estado. Isso não é apenas
  a11y — é o modo de operação preferido de um usuário avançado em desktop.
- Estados de carregamento, erro e vazio em telas densas devem preservar a
  estrutura da grade/tabela (skeleton na forma da linha/coluna real) para
  não quebrar o ritmo de escaneamento do operador.

## Fora de escopo (fica em outra skill)

- Arquitetura de componentes, hooks, TypeScript, testes, CSP, segurança de
  código → skill de **engenharia** da stack (ex.: `expert-frontend-react`).
- Nome do Design System, tokens de cor/paleta concretos, tipografia,
  biblioteca de componentes → `CLAUDE.md` do projeto ou skill de marca.
- UX mobile-first (alvo de toque, gestos, navegação por polegar,
  offline/PWA) → `expert-frontend-pwa`.
