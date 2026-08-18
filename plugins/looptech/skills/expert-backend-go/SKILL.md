---
name: expert-backend-go
description: Disciplina de ENGENHARIA backend em Go — arquitetura em camadas/hexagonal e desacoplamento por interfaces (ports), disciplina sqlx (named query consts, zero SELECT *, params $N/:param, null.T), pirâmide de testes (unit + testcontainers + injection tests) e lint golangci na forma only-new-issues. Carregue ao trabalhar em qualquer sub-projeto cuja stack seja Go (go.mod presente). Despachada pelo workflow-dev; comandos concretos vêm do Project Profile. Execução de query/migration é delegada a expert-database.
---

# Expert Backend Go — Disciplina de Engenharia

Esta skill carrega **processo e disciplina transferível** para qualquer backend Go,
independentemente do produto. Fatos concretos (paths, comandos exatos, nomes de tabela,
nomes de função de negócio) vêm do Project Profile (`CLAUDE.md` / `AGENTS.md`) do projeto — nunca desta skill.

> **Escopo:** só engenharia (arquitetura, sqlx, testes, lint, segurança em princípio).
> A **execução** de query/migration (discovery de schema, gate de produção, aplicação de
> migration) é responsabilidade de `looptech:expert-database` — delegue para lá.

---

## 1. Arquitetura em camadas / hexagonal

- Separe o código em camadas explícitas: domínio (regras de negócio puras) → aplicação
  (casos de uso/orquestração) → infraestrutura (HTTP, banco, filas, provedores externos).
  A direção da dependência é sempre de fora para dentro — infraestrutura depende do
  domínio, nunca o contrário.
- **Desacople por interfaces (ports).** Toda dependência externa (repositório, gateway de
  pagamento, provedor de IA, fila) é consumida via uma interface definida no domínio/aplicação
  (`port`), com a implementação concreta (`adapter`) vivendo na camada de infraestrutura.
  Isso permite trocar a implementação (ou mockar em teste) sem tocar a regra de negócio.
- **Injeção de dependência** explícita (construtor recebe as interfaces de que precisa;
  nada de singleton global escondido ou `init()` mágico resolvendo dependência). Um
  container de DI (ex.: `fx`, `wire`, ou wiring manual) é aceitável desde que o grafo de
  dependências seja verificável — se o projeto usa um framework de DI com validação em boot,
  rode essa validação antes de considerar a tarefa pronta.
- Casos de uso não devem importar tipos de infraestrutura diretamente (ex.: um `UseCase`
  não referencia um driver de banco específico) — só a interface (`port`).
- Erros de domínio são tipados/sentinela (`ports.ErrX`), não `errors.New` genérico
  espalhado, para permitir tratamento diferenciado por camada (ex.: 404 vs 500 numa borda
  HTTP).

---

## 2. Disciplina `sqlx` (acesso a banco relacional)

Estas regras valem para todo código que compõe SQL via `sqlx` (ou biblioteca equivalente
de binding por struct tag). São **não-negociáveis** — todo PR que toca a camada de dados
deve respeitá-las antes de merge.

### 2.1 Named query constants

Toda query SQL de string fixa é um `const` no nível do pacote, nunca uma string inline
dentro do corpo de um método. Convenção de nome: `query<Verbo><Entidade>[Qualificador]`
(`Create`, `Get`, `List`, `Update`, `Delete`, `Count`, `Check`, `Upsert`).

```go
const entityColumns = `
    id, name, status, created_at, updated_at
`

const (
    queryCreateEntity = `
        INSERT INTO entities (id, name, status, created_at)
        VALUES (:id, :name, :status, :created_at)
    `
    queryGetEntityByID = `SELECT ` + entityColumns + ` FROM entities WHERE id = $1`
    queryListEntitiesByStatus = `
        SELECT ` + entityColumns + ` FROM entities
        WHERE status = $1
        ORDER BY created_at DESC
    `
)
```

Para queries montadas condicionalmente (WHERE dinâmico), extraia os trechos **estáticos**
como consts e mantenha só a lógica de montagem em runtime no corpo do método.

### 2.2 Zero `SELECT *` — colunas sempre explícitas

`SELECT *` é proibido em qualquer query de repositório. Defina um `const <tabela>Columns`
por tabela e reutilize-o em todas as queries daquela tabela.

Motivo: bindings por struct tag (`db:""`) mapeiam por nome de coluna. Uma migration que
adiciona coluna antes do deploy do código quebra `SELECT *` em produção com erro de
"missing destination name" — `SELECT *` acopla o schema físico ao deploy, silenciosamente.

Para JOINs, liste as colunas com prefixo de tabela inline na própria query (não tente
reaproveitar o const base com alias — isso confunde mais do que ajuda).

### 2.3 Valores só como parâmetro — nunca interpolados

Todo valor de origem externa ou controlado pelo usuário é vinculado como parâmetro —
posicional (`$N`) para queries de aridade fixa, nomeado (`:campo`) para INSERT/UPDATE com
muitos campos via `NamedExecContext`. Nunca concatenação/`fmt.Sprintf` de valor para dentro
da string SQL — isso vale também para tipos não-string (int, bool, tempo): até esses vão
como parâmetro.

Em WHERE dinâmico, numere o parâmetro a partir de `len(args)` **depois** de dar `append`
no valor, para evitar off-by-one e manter os valores fora da string SQL.

### 2.4 Sem `COALESCE` desnecessário em coluna já `*T`

Não envolva coluna nullable em `COALESCE` quando o campo Go correspondente já é ponteiro
(`*string`, `*int64`, `*time.Time`) ou um tipo `null.T`. O binding já mapeia `NULL → nil`
nativamente, e `COALESCE` sobre coluna indexada impede o planner de usar o índice.
`COALESCE` continua aceitável sobre função de agregação (`COALESCE(SUM(x), 0)`) ou
fallback aritmético entre duas colunas — aí não há índice a proteger.

### 2.5 `null.T` para campo nullable novo

Ao adicionar um campo nullable a uma struct que também precisa de serialização JSON
correta (NULL → `null` no JSON, não `""`/`0`), prefira um tipo `null.T` (`null.String`,
`null.Int64`, `null.Float64`, `null.Bool`, `null.Time`) a um ponteiro cru. Ponteiro cru
continua aceitável para campo oculto do JSON (`json:"-"`) ou puramente interno ao
repositório.

### 2.6 Migration parity

Toda coluna nova exige migration (par up/down) **e** atualização do `const <tabela>Columns`
correspondente na mesma PR — os dois nunca podem divergir. A **execução** da migration em
si (ordem, validação de existência antes de aplicar, tracking de versão) é responsabilidade
de `looptech:expert-database`.

---

## 3. Pirâmide de testes

| Camada | Tipo de teste | Ferramenta |
|---|---|---|
| Lógica pura / domínio | Unit test | `go test` |
| Repositório (acesso a dados) | Integração | testcontainers (container real do banco) |
| Endpoint de API | Integração | servidor HTTP real + banco de teste |

- **Unit tests** cobrem regra de negócio isolada do domínio/aplicação — sem I/O, sem banco,
  dependências externas mockadas via as interfaces (`ports`) da camada de arquitetura.
- **Testes de integração** (`testcontainers`) sobem um container real do banco por execução
  de suíte (não um container por teste) e rodam as migrations uma vez; cada teste limpa seu
  próprio dado (`t.Cleanup`). Todo repositório novo precisa de arquivo de integração cobrindo
  seus métodos públicos: write→read roundtrip, campo nullable escaneando como `nil`/inválido
  sem erro, campo não-nulo correto após roundtrip, comportamento de update, e caminho
  not-found retornando `nil, nil` (não um erro).
- **Injection tests** — todo método de repositório que aceita `string`/`*string` vindo de
  fora da camada de serviço precisa de teste de injeção de SQL. Rode uma lista padrão de
  payloads (`' OR '1'='1`, `'; DROP TABLE x; --`, `' UNION SELECT ...`, `' OR SLEEP(5) --`,
  etc. — evite payload com byte nulo, muitos bancos rejeitam como UTF-8 inválido). Para
  método de **busca**: o payload não deve casar nenhuma linha e não deve gerar erro de SQL.
  Para método de **escrita**: o payload deve ser armazenado e recuperado **literalmente**
  (prova de que foi tratado como dado, não como comando).

---

## 4. Lint — espelhando o CI

`golangci-lint` é o meta-linter Go de referência (agrega `govet`, `staticcheck`,
`errcheck`, `ineffassign`, `unused`, `gosimple`, entre outros). A forma correta de rodá-lo
localmente é **only-new-issues**, espelhando o que o CI real roda — não o full-repo scan.

O princípio: rodar lint só-linhas-novas contra a branch base evita dois erros comuns —
(a) tratar o full-repo scan (com centenas de achados pré-existentes) como gate de
pass/fail, e (b) racionalizar um achado only-new-issues como "já existia antes" quando na
verdade a linha que você tocou conta como nova mesmo que o padrão já existisse em outro
lugar do repositório.

O **comando exato** (branch base, flags, se roda `go vet` junto) vem do Project Profile do
projeto — esta skill não hardcoda um comando, só o princípio de que o gate correto é
only-new-issues e deve imprimir "zero issues" antes de considerar a task pronta.

---

## 5. Segurança — em princípio (product-neutral)

Estes são princípios de engenharia backend, válidos para qualquer produto. Regras de
segurança **específicas do produto** (nome de lock, nome de variável de ambiente de scope,
allowlist de CORS, etc.) ficam no Project Profile do projeto, não nesta skill.

- **Ownership em todo acesso a recurso.** Toda rota que acessa um recurso identificado por
  ID deve verificar que o dono do recurso é o usuário autenticado (ou que o chamador tem
  papel administrativo explícito) — nunca confiar que um ID "difícil de adivinhar" seja
  suficiente controle de acesso.
- **Serializar mutações financeiras com lock de banco.** Qualquer operação que lê um saldo
  e decide sobre ele (criar uma cobrança, um saque, um estorno) deve serializar por chave de
  negócio (ex.: por conta/usuário) usando um lock transacional do banco (advisory lock ou
  equivalente), com leitura e escrita **na mesma transação**. Nunca calcular saldo numa
  transação e efetivar a mutação em outra — essa janela é a origem clássica de
  double-spend/corrida.
- **Gatear endpoints internos/de debug por ambiente.** Qualquer rota que exponha schema
  interno, spec de API, ou ferramental de debug deve ser condicionada a uma variável de
  ambiente de escopo, nunca exposta por padrão em ambiente de staging/produção.
- **Nunca confiar em `role`/papel vindo do input do usuário.** Todo campo de papel/role
  recebido em registro ou atualização deve ser validado contra uma allowlist fechada de
  papéis não-administrativos; contas com privilégio administrativo são criadas fora desse
  fluxo.

---

## 6. Delegação — o que NÃO é desta skill

- **Execução de query/migration** (discovery de schema ao vivo, pre-flight de conexão,
  gate de produção, ordem de aplicação de migration por existência) → `looptech:expert-database`.
- **Fatos concretos** (comandos exatos de test/lint/build, nome de conexão de banco,
  convenção de branch/PR) → Project Profile no `CLAUDE.md` / `AGENTS.md`, resolvido pelo
  `looptech:workflow-dev`.
- **Regras de segurança específicas do produto** (nome de função/lock, allowlist de CORS
  concreta, nome de variável de scope) → Project Profile do projeto.

---

## Checklist de PR (engenharia backend Go)

- [ ] Toda query SQL é `const` — nenhuma string de query inline no corpo de método
- [ ] Zero `SELECT *` — todo SELECT lista colunas explicitamente via `const <tabela>Columns`
- [ ] Todo valor passa como `$N` ou `:param` — nenhuma interpolação de string em SQL
- [ ] Sem `COALESCE` em coluna cujo campo Go já é `*T`
- [ ] Dependências externas desacopladas por interface (`port`), implementação em adapter
- [ ] Teste de integração cobre write→read roundtrip, nullable, not-found path
- [ ] Teste de injeção de SQL cobre todo parâmetro `string`/`*string` externo
- [ ] Campo nullable novo usa `null.T` quando a serialização JSON importa
- [ ] Coluna nova tem migration **e** `<tabela>Columns` atualizado na mesma PR
- [ ] Todo acesso a recurso verifica ownership (não só autenticação)
- [ ] Mutação financeira serializada por lock de banco, leitura+escrita na mesma transação
- [ ] Lint limpo na forma only-new-issues (comando exato do Project Profile)
- [ ] Testes unitários e de integração passam

## Red flags

- SQL inline no corpo do método (não é `const`)
- `SELECT *` em qualquer lugar de um repositório
- Valor de runtime interpolado dentro da string SQL
- Teste de integração ausente para método novo de repositório
- Mutação financeira fora de um bloco de lock transacional
- Rota administrativa sem middleware de restrição administrativa
- Acesso a recurso sem checagem de ownership
- Caso de uso importando tipo concreto de infraestrutura em vez de interface (`port`)
