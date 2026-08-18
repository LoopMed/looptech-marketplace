---
name: expert-frontend-vue
description: Disciplina de ENGENHARIA frontend em Vue 3 + TypeScript (não trata de UX/layout — isso é expert-frontend-pwa/web) — SFC com script setup, composables isolados e testáveis, TypeScript strict (sem any/@ts-ignore sem justificativa), testes vitest + Vue Testing Library focados em comportamento visível (ByRole/ByLabelText), E2E no golden path, CSP declarada no config de deploy, sem segredos no client, backend como autoridade de authz. Carregue ao trabalhar em qualquer sub-projeto cuja stack seja Vue (package.json com vue). Despachada pelo workflow-dev junto com a skill de UX da área; comandos concretos vêm do Project Profile; Design System/UI kit e camadas concretas vêm das skills locais do projeto.
---

# expert-frontend-vue — Engenharia Vue 3 + TypeScript

Skill agnóstica de produto. Cobre **só engenharia**: arquitetura de SFCs/composables,
tipagem, testes e segurança em princípio. **UX, layout, densidade, mobile-first vs.
web-first e qualquer decisão de interação vivem em `expert-frontend-pwa` /
`expert-frontend-web`** — o `workflow-dev` despacha essa skill de UX **junto** com esta,
resolvida por área via o Project Profile (`ux_default` / `ux_overrides`) do `CLAUDE.md` /
`AGENTS.md` do projeto.

Fatos concretos (comandos de teste/lint/build, Design System, UI kit, estrutura de pastas,
gotchas de deploy) **não** vivem aqui — vêm do Project Profile e das skills/regras locais
do projeto (ex.: `architecture-*`, `ui-*`). Esta skill carrega a disciplina; o projeto
carrega os fatos.

---

## Arquitetura de SFCs e desacoplamento

- SFCs pequenos, com responsabilidade única; separar apresentação de lógica de dados.
- Preferir `<script setup lang="ts">` em código novo.
- **Composables isolados e testáveis**: extrair lógica com estado/efeitos para
  `useX` próprios, testáveis sem montar a árvore de views inteira.
- Evitar prop-drilling profundo e acoplamento a detalhes de um componente distante —
  prefira composição, slots e contratos de props/emits explícitos.
- Chamadas de rede/dados isoladas numa camada própria (api client / repository /
  composable de dados), nunca espalhadas dentro de componentes de apresentação.
- Preferir `defineModel` / props+emits tipados a `v-model` frouxo em componentes de
  formulário reutilizáveis.
- Estado global (Pinia ou equivalente do projeto) só para o que realmente é
  cross-route; o resto fica local ao composable/view.

---

## TypeScript

- **Strict mode** é a primeira linha de defesa — o compilador deve travar o build em
  erro de tipo (em especial quando o build de produção roda typecheck, ex. `vue-tsc`).
- **Todo `ref` que começa `null` precisa de genérico** — `ref<T | null>(null)`. Sem isso
  o tipo vira `never` e quebra o build.
- **Todo `catch` tipa o erro** — `catch (e: unknown)` + narrowing (ou o padrão já
  estabelecido no arquivo).
- **Sem `any`** sem um comentário explicando por quê — prefira tipos próprios ou
  `unknown` com narrowing.
- **Sem `@ts-ignore` / `@ts-expect-error`** sem referência a um ticket de follow-up.
- **Sem `console.log`** em código de produção — remover antes de abrir PR.
- Não assumir que componentes de UI kit aceitam `number` em `v-model` string-only —
  use bridge `computed` ou `:model-value` + `@update:model-value`.

---

## Testes

| Camada | Tipo de teste | Ferramenta |
|--------|----------------|------------|
| Lógica pura / composables | Unit test | vitest |
| Componentes Vue | Component test | vitest + Vue Testing Library (ou `@vue/test-utils`) |
| Fluxos de usuário (golden path) | E2E | Playwright (ou equivalente do projeto) |

- **Teste comportamento visível, não implementação**: asserts sobre o que o usuário
  vê/faz, nunca sobre estado interno do setup ou detalhes de renderização.
- **Queries por acessibilidade primeiro**: prefira `ByRole` / `ByLabelText` / `ByText`
  a `ByTestId` — `data-testid` é último recurso.
- **Mock no boundary de rede** (MSW ou equivalente), nunca mockando o componente ou a
  camada de dados por dentro.
- **E2E cobre o golden path** de todo fluxo novo voltado ao usuário — edge cases ficam
  em unit/component.
- Comandos concretos (`test`, `e2e`, `lint`, `types`, `build`) vêm do bloco `commands`
  do Project Profile — nunca hardcode aqui.

---

## Segurança em princípio

Estas são regras de **engenharia transferíveis**; origens/domínios concretos e o arquivo
de config de deploy vêm do Project Profile / skills locais do projeto.

- **CSP declarada no config de deploy**. Ao adicionar script/iframe/origem externa nova,
  **atualizar a CSP na mesma PR** — nunca contornar com `unsafe-inline`/`unsafe-eval`.
- **Sem segredos no client**: nenhuma API key, token ou segredo em código-fonte.
  Variáveis `VITE_*` (ou equivalentes) só para identificadores públicos.
- **Nunca logar token de autenticação ou PII** no console do navegador.
- **Backend é a autoridade de authz** — checagem de `role` no frontend é **só UX**,
  nunca controle de acesso real.

---

## Checklist de PR (Frontend — engenharia)

```
- [ ] Nenhuma origem externa nova sem atualizar a CSP do config de deploy
- [ ] Sem segredos/tokens em código-fonte ou em console.log
- [ ] Gating de UI por role tem checagem de autorização correspondente na API
- [ ] Sem cast `any` sem comentário explicando o motivo
- [ ] Sem `@ts-ignore` / `@ts-expect-error` sem ticket de follow-up
- [ ] `ref(null)` tipado; `catch` tipado
- [ ] Testes unit/component passam (comando do Project Profile)
- [ ] Testes E2E do golden path passam (comando do Project Profile), se houver
- [ ] Lint limpo (comando do Project Profile)
- [ ] Typecheck / build de produção sucede (comando do Project Profile)
```

---

## Red Flags

- Origem/script/iframe externo novo sem atualização de CSP no mesmo PR.
- `ref(null)` sem genérico → tipo `never` quebrando `vue-tsc`/deploy.
- Cast `any` ou `@ts-ignore` sem justificativa.
- `console.log` esquecido em código de produção.
- Token de auth ou PII logado no console do navegador.
- Checagem de role só no frontend, sem autorização correspondente no backend.
- Composable com lógica de estado/efeito não extraível/testável isoladamente.
- Teste acoplado a implementação interna, não a comportamento visível.
- Build de produção / typecheck falhando antes de abrir PR.

---

## Fora de escopo desta skill

Layout, densidade de informação, mobile-first vs. web-first, alvos de toque, atalhos de
teclado, estados de conectividade/offline, Design System e paleta — tudo isso é
**UX/interação**, coberto por `expert-frontend-pwa` (mobile-first) ou
`expert-frontend-web` (web-first), despachada pelo `workflow-dev` conforme a área do
Project Profile.

Detalhes de produto (PrimeVue vs Naive UI, pastas, auth Firebase, proxy `/api`, etc.)
vivem nas **skills locais do repositório** — carregue-as junto quando o Profile ou a
tarefa apontar para aquele produto.
