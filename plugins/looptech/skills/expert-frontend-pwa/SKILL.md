---
name: expert-frontend-pwa
description: Disciplina de UI/UX/interação orientada a MOBILE-FIRST (agnóstica de produto; Design System e paleta concretos vêm do Project Profile). Layout do menor breakpoint para cima, alvos de toque ≥44px, navegação por polegar, hover nunca como único caminho, densidade enxuta, performance percebida (skeletons, JS/imagem leves) e comportamento PWA/offline quando aplicável. Carregue (junto com a skill de engenharia da stack) ao tocar áreas de frontend marcadas como mobile-first no Project Profile (ux_default/ux_overrides). NÃO cobre arquitetura/TS/testes — isso é o eixo de engenharia (ex.: expert-frontend-react ou expert-frontend-vue).
---

# Expert Frontend PWA — UX Mobile-First

## Escopo desta skill

Esta skill cobre **só o eixo de UX/UI/interação orientado a mobile**. Ela **compõe** com a
skill de engenharia da stack (ex.: `expert-frontend-react` / `expert-frontend-vue`) — nunca a substitui.

- **Cobre:** decisões de layout, densidade, ergonomia de toque, performance percebida e
  comportamento PWA/offline.
- **NÃO cobre:** arquitetura de componentes, TypeScript, testes, build, CSP, ou qualquer
  disciplina de engenharia — isso é responsabilidade da skill de engenharia da stack, que
  deve ser carregada junto.
- **NÃO define** paleta, tokens de Design System, nomes de componentes ou paths concretos —
  esses fatos vêm sempre do Project Profile (`CLAUDE.md` / `AGENTS.md`) do projeto.

Carregue esta skill quando o `workflow-dev` resolver, via Project Profile
(`ux_default`/`ux_overrides`), que a área de frontend tocada é mobile-first — tipicamente o
app principal voltado ao usuário final em um dispositivo móvel.

---

## 1. Mobile-first por padrão

- **Layout do menor breakpoint para cima:** desenhe e implemente primeiro para a tela mais
  estreita realista; breakpoints maiores são progressive enhancement, nunca o ponto de
  partida. Nunca projete em desktop e "encolha" depois.
- **Alvos de toque ≥ 44px:** todo elemento interativo (botão, ícone, item de lista, checkbox)
  precisa de uma área de toque mínima de 44×44px, mesmo que o elemento visual seja menor —
  use padding para compensar.
- **Gestos e navegação por polegar:** priorize ações alcançáveis com uma mão — swipe,
  pull-to-refresh, navegação inferior (tab bar) em vez de superior quando fizer sentido para
  o fluxo. Considere a "zona do polegar": o terço inferior da tela é o mais acessível em uso
  com uma mão.
- **Hover nunca como único caminho:** nenhuma informação ou ação pode depender
  exclusivamente de `:hover` — dispositivos de toque não têm hover. Todo estado revelado por
  hover precisa de um equivalente por toque/foco (tap, long-press, ou visível por padrão).

## 2. Densidade e ergonomia

- **Essencial acima da dobra:** a informação e a ação mais importante da tela devem estar
  visíveis sem scroll na viewport mobile padrão. Não enterre a ação primária sob conteúdo
  secundário.
- **Ações primárias ao alcance do polegar:** posicione o CTA principal na metade inferior da
  tela ou fixo (sticky) quando o fluxo for longo — evite forçar o usuário a esticar o
  polegar até o topo.
- **Teclados e inputmodes adequados:** todo campo de formulário deve disparar o teclado
  correto (`inputmode="numeric"` para números, `type="email"` para e-mail, `type="tel"` para
  telefone) — reduz erro de digitação e fricção em telas pequenas.
- **Densidade enxuta:** menos elementos por tela do que uma versão desktop equivalente;
  prefira revelar detalhes sob demanda (expandir, navegar para outra tela) a comprimir tudo
  em uma única view.

## 3. Performance percebida

- **Skeletons em vez de spinners genéricos:** ao carregar conteúdo, mostre a forma
  aproximada do resultado final (skeleton screens) em vez de um spinner central — reduz a
  sensação de espera.
- **Atualização otimista quando cabível:** para ações de baixo risco e alta frequência
  (curtir, marcar como lido, favoritar), atualize a UI imediatamente e reconcilie com o
  servidor em background, com rollback visível em caso de falha.
- **JS e imagem leves:** o público mobile está em rede variável (3G/4G instável, dados
  limitados) — priorize bundles pequenos, lazy-load de rotas/imagens fora da viewport
  inicial, e formatos de imagem comprimidos/responsivos.

## 4. PWA e comportamento offline

- **Offline-tolerante quando o projeto for PWA:** ações críticas devem degradar
  graciosamente sem rede — enfileirar e sincronizar depois, ou informar claramente que a
  ação requer conexão, nunca falhar silenciosamente.
- **Estados de conectividade visíveis:** quando a app for PWA, sinalize ao usuário quando
  estiver offline ou com conexão instável (banner, indicador), especialmente antes de ações
  que dependem de rede.
- **Foco e estados acessíveis por toque:** todo estado interativo (focus, active, disabled,
  loading) precisa ser perceptível via toque, não só via teclado/mouse — feedback visual
  imediato ao tocar (ripple, opacity, scale) confirma que a ação foi registrada.

---

## O que esta skill assume que já está resolvido

- Arquitetura de componentes, tipagem, testes e build: cobertos pela skill de engenharia da
  stack (ex.: `expert-frontend-react` / `expert-frontend-vue`), carregada em conjunto.
- Design System, paleta, tokens, nomes de componentes concretos: vêm do Project Profile do
  projeto.
- Qual área do frontend é mobile-first vs. web-first: resolvido pelo `workflow-dev` via
  `ux_default`/`ux_overrides` no Project Profile — esta skill não decide isso, só aplica a
  disciplina depois que a área já foi classificada como mobile-first.
