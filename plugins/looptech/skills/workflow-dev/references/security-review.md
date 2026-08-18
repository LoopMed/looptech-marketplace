# Security review — falhas que podem prejudicar a empresa

Etapa obrigatória **antes de cada commit**, no mesmo diff do review de correção.
Readonly: o subagente `security` **não escreve código**. Achado vira
`ISSUES-FOUND` e volta para um subagente `impl`.

O alvo não é estilo. É dano: perda de dinheiro, vazamento de dado, takeover de
conta, fraude, incidente público, ou porta dos fundos em produção.

## Quando roda

- **Toda lane, todo commit de código.** Roda em paralelo com o review de
  correção no mesmo diff (não serializa `review → security` por hábito).
- **Pula só** se o diff inteiro for não-runtime (docs, comentário, changelog,
  typo de texto) **e** o orquestrador declarar o pulo em voz alta.
- Superfície sensível (auth, sessão, token, pagamento, PII, persistência,
  API pública, upload, CORS, secret/env, papel/admin, webhook) **nunca** pula,
  nem na lane S.

## Entrada (orquestrador cola)

Além dos quatro blocos de `subagent-handoff.md`:

1. O **diff completo** da task (mesmo do review de correção).
2. As 5–15 linhas de **segurança em princípio** da skill expert da stack
   tocada (ownership, lock, gating, CSP, authz no backend).
3. Regras de segurança **do produto** no Project Profile, se existirem
   (nome de lock, allowlist, variável de scope). Sem elas, não invente —
   use só os princípios agnósticos abaixo.
4. Se o papel `security` caiu em `critique` (sem especialista no host),
   cole **esta página inteira** e diga isso no Objetivo Final.

## O que caçar (agnóstico)

Cada item é um veredito binário: presente no diff / não. Sem achado, não
preencha com hipótese.

| Classe | Prejuízo | Sinais no diff |
|---|---|---|
| Segredo | Credencial no git, no log, no client | token, password, private key, connection string, `.env` commitado, `VITE_*`/`NEXT_PUBLIC_*` com segredo |
| Authz | Takeover / IDOR / escalada | recurso por ID sem ownership; `role` vindo do client; 403 que vaza existência; método RAW multi-tenant em rota de request |
| Authn | Sessão forjada / bypass | token em query string; cookie sem flags; trust em header forjável |
| Injection | Leitura/escrita arbitrária | SQL/comando/template interpolado; path traversal; unsanitized HTML |
| Dinheiro / estado | Double-spend, fraude, corrida | saldo/estoque lido numa transação e mutado em outra; falta de lock; idempotência ausente em webhook de pagamento |
| PII | Vazamento / LGPD | CPF/e-mail/dado fiscal em log, URL, erro, analytics; resposta demais no dump |
| Superfície interna | Porta dos fundos em prod | debug, swagger, admin, metrics sem gate de ambiente; CORS `*` com credencial |
| Input untrusted | SSRF, open redirect, upload | URL do usuário virando fetch interno; redirect sem allowlist; arquivo sem tipo/tamanho |
| Crypto / token | Sessão roubável | secret hardcoded; JWT sem expiração; comparação não-constante de secret |

Não é lista fechada. Se o diff cria um jeito novo de um estranho (ou um
usuário comum) ler, mutar ou gastar o que não é dele — é achado.

## Veredito (obrigatório no retorno)

Depois das três seções de `subagent-handoff.md`, feche com **uma** linha:

```
VEREDITO: SECURE
```

ou

```
VEREDITO: ISSUES-FOUND
```

- **SECURE** — nenhum item da tabela (nem outro dano equivalente) está no diff.
  Evidências listam o que foi checado, não um “parece ok”.
- **ISSUES-FOUND** — cada achado tem: classe, path, por que prejudica a
  empresa, e o remédio mínimo. Sem remédio inventado além do que o diff pede.

`SECURE` com zero evidências de checagem é review inválida — o orquestrador
manda refazer, não commita.

## Depois do veredito

| Veredito | Orquestrador |
|---|---|
| `SECURE` e review de correção `APPROVE` | commit |
| `ISSUES-FOUND` | novo `impl` com os achados colados → **re-review de correção e de segurança** no diff novo |
| Correção `CHANGES-REQUESTED` | mesmo loop; security só re-roda no diff ajustado |

O orquestrador nunca aplica o fix de segurança ele mesmo (exceto ≤ 100
caracteres). Nunca commita com `ISSUES-FOUND` em aberto, nem porque “é só um
warning”.
