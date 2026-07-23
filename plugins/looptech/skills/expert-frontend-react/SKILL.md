---
name: expert-frontend-react
description: Disciplina de ENGENHARIA frontend em React + TypeScript (não trata de UX/layout — isso é expert-frontend-pwa/web) — arquitetura de componentes e desacoplamento, hooks isolados e testáveis, TypeScript strict (sem any/@ts-ignore sem justificativa), testes vitest + Testing Library focados em comportamento visível (ByRole/ByLabelText), E2E no golden path, CSP declarada no config de deploy, sem segredos no client, backend como autoridade de authz. Carregue ao trabalhar em qualquer sub-projeto cuja stack seja React (package.json com react). Despachada pelo workflow-dev junto com a skill de UX da área; comandos concretos vêm do Project Profile.
---

# expert-frontend-react — Engenharia React + TypeScript

Skill agnóstica de produto. Cobre **só engenharia**: arquitetura de componentes, tipagem,
testes e segurança em princípio. **UX, layout, densidade, mobile-first vs. web-first e
qualquer decisão de interação vivem em `expert-frontend-pwa` / `expert-frontend-web`** —
o `workflow-dev` despacha essa skill de UX **junto** com esta, resolvida por área via o
Project Profile (`ux_default` / `ux_overrides`) do `CLAUDE.md` do projeto.

Fatos concretos (comandos de teste/lint/build, nome do arquivo de config de deploy, origens
externas permitidas na CSP, Design System) **não** vivem aqui — vêm do Project Profile e das
skills/regras locais do projeto. Esta skill carrega a disciplina; o `CLAUDE.md` carrega os
fatos.

---

## Arquitetura de componentes e desacoplamento

- Componentes pequenos, com responsabilidade única; separar apresentação de lógica de dados.
- **Hooks isolados e testáveis**: extrair lógica com estado/efeitos para hooks próprios,
  testáveis sem montar a árvore de componentes inteira.
- Evitar prop-drilling profundo e acoplamento a detalhes de implementação de um componente
  distante — prefira composição e contratos de props explícitos.
- Chamadas de rede/dados isoladas numa camada própria (client/service/hook de dados), nunca
  espalhadas dentro de componentes de apresentação.

---

## TypeScript

- **Strict mode** é a primeira linha de defesa — o compilador deve travar o build em erro
  de tipo, não apenas o lint.
- **Sem `any`** sem um comentário explicando por quê — prefira tipos próprios ou `unknown`
  com narrowing.
- **Sem `@ts-ignore`** sem referência a um ticket de follow-up no comentário.
- **Sem `console.log`** em código de produção — remover antes de abrir PR; usar logging
  estruturado ou remover de vez.

---

## Testes

| Camada | Tipo de teste | Ferramenta |
|--------|----------------|------------|
| Lógica pura / hooks | Unit test | vitest |
| Componentes React | Component test | vitest + Testing Library |
| Fluxos de usuário (golden path) | E2E | Playwright (ou equivalente do projeto) |

- **Teste comportamento visível, não implementação**: asserts sobre o que o usuário vê/faz,
  nunca sobre estado interno ou detalhes de renderização.
- **Queries por acessibilidade primeiro**: prefira `ByRole` / `ByLabelText` / `ByText` a
  `ByTestId` — um seletor `data-testid` é o último recurso, não o padrão.
- **Mock no boundary de rede** (ex.: MSW), nunca mockando o componente ou a camada de dados
  por dentro — o teste deve validar o componente real conversando com uma rede simulada.
- **E2E cobre o golden path** de todo fluxo novo voltado ao usuário — não é para cobrir
  edge cases, isso fica para unit/component.
- Comandos concretos (`test`, `e2e`, `lint`, `types`, `build`) vêm do bloco `commands` do
  Project Profile — nunca hardcode aqui.

---

## Segurança em princípio

Estas são regras de **engenharia transferíveis**; as origens/domínios concretos permitidos
e o arquivo de config de deploy exato vêm do `CLAUDE.md` do projeto.

- **CSP declarada no config de deploy** (o mecanismo depende da plataforma do projeto —
  pode ser um header de config de hosting, um middleware, meta tag, etc.). Ao adicionar
  qualquer script/iframe/origem externa nova, **atualizar a CSP na mesma PR** — nunca
  contornar com `unsafe-inline`/`unsafe-eval`.
- **Sem segredos no client**: nenhuma API key, token ou segredo em código-fonte JS/TS.
  Variáveis de ambiente expostas ao client só para identificadores públicos.
- **Nunca logar token de autenticação ou PII** no console do navegador.
- **Backend é a autoridade de authz** — checagem de `role` no frontend é **só UX**, nunca
  controle de acesso real. Nunca confiar em `role` armazenado no client (localStorage etc.)
  sem validação server-side na ação sensível correspondente.

---

## Checklist de PR (Frontend — engenharia)

```
- [ ] Nenhuma origem externa nova sem atualizar a CSP do config de deploy
- [ ] Sem segredos/tokens em código-fonte ou em console.log
- [ ] Gating de UI por role tem checagem de autorização correspondente na API
- [ ] Sem cast `any` sem comentário explicando o motivo
- [ ] Sem `@ts-ignore` sem referência a ticket de follow-up
- [ ] Testes unit/component passam (comando do Project Profile)
- [ ] Testes E2E do golden path passam (comando do Project Profile)
- [ ] Lint limpo (comando do Project Profile)
- [ ] Typecheck limpo (comando do Project Profile)
- [ ] Build de produção sucede (comando do Project Profile)
```

---

## Red Flags

- Origem/script/iframe externo novo sem atualização de CSP no mesmo PR.
- Cast `any` sem comentário explicando o motivo.
- `console.log` esquecido em código de produção.
- Token de auth ou PII logado no console do navegador.
- Checagem de role só no frontend, sem autorização correspondente no backend.
- Hook com lógica de estado/efeito não extraível/testável isoladamente do componente.
- Teste que quebra ao refatorar detalhe interno sem mudar comportamento visível (teste
  acoplado a implementação, não a comportamento).
- Build de produção falhando ou lint com erros commitados antes de abrir PR.

---

## Fora de escopo desta skill

Layout, densidade de informação, mobile-first vs. web-first, alvos de toque, atalhos de
teclado, estados de conectividade/offline, Design System e paleta — tudo isso é
**UX/interação**, coberto por `expert-frontend-pwa` (mobile-first) ou `expert-frontend-web`
(web-first), despachada pelo `workflow-dev` conforme a área do Project Profile.
