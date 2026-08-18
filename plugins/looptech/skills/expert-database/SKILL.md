---
name: expert-database
description: Disciplina e execução de banco de dados relacional (dialeto de referência Postgres), agnóstica ao produto. Metade A — disciplina de query: named query consts, zero SELECT *, valores só $N/:param, null.T para nullable, injection tests, testes de integração com container. Metade B — fluxo de execução: preflight de conexão (com onboarding passo a passo se não houver base configurada) → descobrir tabelas → schemas → indexes → montar query sargável → executar; produção SEMPRE exige validação humana; migrations por EXISTÊNCIA da estrutura (não por version). Carregue sempre que a tarefa tocar a camada de persistência/DB. Fatos de conexão vêm do bloco database do Project Profile.
---

# expert-database — Disciplina de Query + Fluxo de Execução

Skill agnóstica de produto e de dialeto. Cobre **duas metades**: (A) a disciplina de
como escrever/estruturar queries no código do repositório, e (B) o fluxo operacional de
como conectar, descobrir schema ao vivo e executar — incluindo o gate de produção e a
regra de migration por existência.

**Postgres é o dialeto de referência** desta skill (a sintaxe dos exemplos é Postgres),
mas os princípios são portáveis a qualquer banco relacional. Fatos concretos — nomes de
conexão, dialeto real do projeto, comandos de discovery, nome da tabela de tracking de
migration — vêm do bloco `database` do Project Profile (`CLAUDE.md` / `AGENTS.md`). Esta
skill nunca hardcoda um nome de tabela, de conexão ou de produto.

> **Regra de ouro:** não existe dicionário de schema estático confiável. Schema envelhece
> e mente. O schema é **sempre descoberto ao vivo** no host conectado — nunca presuma
> coluna, tipo ou enum de memória.

---

## Metade A — Disciplina de Query (transferível)

Aplica-se a todo código de repositório/camada de persistência, em qualquer stack.

### 1. Named query constants

Toda query SQL que é uma string fixa deve ser um `const` no nível do pacote, definido
logo após o bloco de constantes de colunas.

**Convenção de nome:** `query<Verbo><Entidade>[Qualificador]`

| Verbo | Quando usar |
|---|---|
| `Create` | INSERT |
| `Get` | SELECT retornando uma linha |
| `List` | SELECT retornando múltiplas linhas |
| `Update` | UPDATE |
| `Delete` | DELETE |
| `Count` | SELECT COUNT(...) |
| `Check` | EXISTS / checagem booleana |
| `Upsert` | INSERT ... ON CONFLICT DO UPDATE |

```
// Constante de colunas — definida primeiro
const entityColumns = `
    id, name, status, created_at, updated_at
`

// Constantes de query — definidas após as de colunas, antes de qualquer método
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

**Queries dinâmicas (WHERE condicional):** extraia todos os segmentos **estáticos**
como consts e mantenha só a lógica de montagem em tempo de execução no corpo do método.
Numere parâmetros a partir de `len(args)` para nunca errar o offset:

```
args = append(args, filterValue)
conditions = append(conditions, fmt.Sprintf("column = $%d", len(args)))
```

### 2. Listas de colunas explícitas — zero `SELECT *`

`SELECT *` acopla o código à ordem/existência física das colunas. Se uma migration
adicionar uma coluna antes do deploy do código (ou remover uma que o mapeamento espera),
`SELECT *` quebra em produção no meio do deploy.

Toda query `SELECT` lista colunas explicitamente. Defina um `const <entidade>Columns`
por tabela e reutilize-o em todas as queries dessa tabela.

```
// ERRADO
query := `SELECT * FROM entities WHERE id = $1`

// CORRETO
const entityColumns = `id, name, status, created_at, updated_at`
const queryGetEntityByID = `SELECT ` + entityColumns + ` FROM entities WHERE id = $1`
```

Para JOINs, liste as colunas com prefixo de tabela inline (não tente reaproveitar o
const base com alias — vira confuso):

```
const queryGetEntityWithOwner = `
    SELECT
        e.id, e.status, e.created_at,
        o.name AS owner_name
    FROM entities e
    JOIN owners o ON o.id = e.owner_id
    WHERE e.id = $1
`
```

### 3. Queries parametrizadas — nunca inline de valores

Todo valor vindo de usuário ou de fonte externa deve ser vinculado como parâmetro SQL,
nunca interpolado na string da query — inclusive valores não-string (int, data, etc.).

```
// ERRADO — risco de SQL injection
query := `SELECT ` + cols + ` FROM users WHERE email = '` + email + `'`

// CORRETO — parâmetro posicional
const queryGetUserByEmail = `SELECT ` + userColumns + ` FROM users WHERE email = $1`

// CORRETO — parâmetros nomeados para INSERT/UPDATE com muitos campos
const queryCreatePayment = `
    INSERT INTO payments (id, amount, status)
    VALUES (:id, :amount, :status)
`
```

```
// ERRADO — int inlined direto na query
query := fmt.Sprintf(`WHERE created_at < NOW() - INTERVAL '%d minutes'`, n)

// CORRETO — até inteiro é parametrizado
const queryGetStaleRows = `
    SELECT ` + cols + ` FROM t
    WHERE created_at < NOW() - ($1 * INTERVAL '1 minute')
`
```

### 4. Sem `COALESCE` desnecessário em coluna nullable

Não envolva uma coluna nullable em `COALESCE` quando o campo correspondente no código
já é um tipo opcional (ponteiro, `Option<T>`, `null.T` etc.). `COALESCE` sobre uma coluna
indexada impede o otimizador de usar o índice; o mapeamento ORM/driver já resolve
`NULL → valor-nulo-da-linguagem` nativamente para campos opcionais.

```
-- ERRADO — impede uso de índice
COALESCE(client_ip, '') AS client_ip

-- CORRETO — o driver mapeia NULL para o tipo opcional automaticamente
client_ip
```

Uso aceitável de `COALESCE` (funções de agregação não têm índice a proteger, e fallback
aritmético entre duas colunas é intencional):
```
COALESCE(AVG(rating), 0)
COALESCE(SUM(amount), 0)
COALESCE(a.amount, b.price)
```

### 5. Tipo `Null[T]` para campos nullable novos

Ao adicionar uma coluna nullable nova, prefira um wrapper `null.T`/`Option<T>` da
biblioteca interna do projeto a um ponteiro cru quando o campo também precisa de
serialização JSON correta (`NULL` → `null` no JSON, não um valor zero disfarçado).
Ponteiros crus continuam aceitáveis para campos ocultos do JSON ou puramente internos à
camada de repositório.

### 6. Testes de integração — obrigatórios por repositório

Todo repositório deve ter cobertura de integração rodando contra um banco real (via
container efêmero, não mock). Cada teste deve validar:

1. **Write → Read roundtrip** — dado escrito é idêntico ao lido de volta.
2. **Campos nullable** — `NULL` mapeia para nulo/`Option` vazio sem erro.
3. **Campos não-nulos** — valores corretos após o roundtrip.
4. **Comportamento de update** — campos mutados refletem após update.
5. **Caminho not-found** — `GetByX` retorna vazio/nil (não erro) quando a linha não existe.

A infraestrutura compartilhada de teste deve subir **um** container de banco por suíte,
rodar as migrations uma vez, e compartilhar a conexão entre os testes.

### 7. Testes de SQL injection

Todo método de repositório que aceita um parâmetro string vindo de fora da camada de
serviço deve ter um teste de injection dedicado.

**Payloads padrão** (não incluir bytes nulos — muitos dialetos rejeitam como UTF-8
inválido):
```
' OR '1'='1
'; DROP TABLE t; --
' UNION SELECT 1,2,3 --
1' OR 1=1 --
" OR ""="
admin'--
' OR 1=1#
' OR SLEEP(5) --
'; SELECT pg_sleep(5); --
```

**Padrão de asserção:**
- Métodos de **lookup**: o payload deve casar **zero** linhas, e a chamada não deve
  retornar erro de SQL (senão o payload quebrou a query — sinal de concatenação insegura).
- Métodos de **escrita**: o payload deve ser gravado e recuperado **literalmente** —
  provando que foi tratado como dado, nunca como SQL.

---

## Metade B — Fluxo de Execução Operacional

Ordem **obrigatória**, sempre nesta sequência — nunca dispare uma query "no escuro" nem
confie em schema de memória:

```
preflight de conexão
  → descobrir nomes das tabelas (discovery LIVE, nunca de memória)
  → descobrir schemas das tabelas
  → descobrir indexes
  → montar a query (sargável, usa índice)
  → executar
```

### Etapa 0 — Preflight de conexão

Antes de qualquer discovery, valide a conexão.

**Se não houver base configurada** (nenhum profile de conexão declarado, ou a conexão
falha ao testar): **PARE** e emita para a dev um passo a passo de onboarding — nunca
avance para discovery/execução com conexão vermelha.

1. **Criar/registrar o profile de conexão** — o nome vem do bloco `database` do Project
   Profile (`CLAUDE.md` / `AGENTS.md`).
2. **Gravar credenciais no secret store do dialeto** (arquivo de credenciais/segredo
   local do cliente do dialeto em uso — nunca em código, nunca em config versionada).
3. **Testar conectividade** com o comando de ping/conexão do dialeto.
4. **Conferir contra o Project Profile** — nome de conexão, dialeto e ambiente (stage/prod)
   batem com o que o bloco `database` declara.

Só com a conexão validada (verde) avance para a Etapa 1.

### Etapa 1 — Descobrir tabelas ("show tables")

Liste as tabelas reais do host conectado — nunca presuma que uma tabela existe.
No dialeto de referência (Postgres):
```sql
\dt
-- ou, portável/scriptável:
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' ORDER BY 1;
```
O comando exato vem de `database.discovery.tables` no Project Profile — outros dialetos
usam sua própria sintaxe de listagem de tabelas.

### Etapa 2 — Descobrir schema (tipo + nullability + enum real)

```sql
\d+ nome_da_tabela
-- ou:
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'nome_da_tabela'
ORDER BY ordinal_position;
```
Para enums textuais, valide os **valores reais** presentes nos dados antes de filtrar —
enums evoluem, um valor histórico pode ter sido removido/renomeado:
```sql
SELECT status, COUNT(*) FROM nome_da_tabela GROUP BY 1 ORDER BY 2 DESC;
```

### Etapa 3 — Descobrir indexes

Decisivo para performance: saber quais colunas têm índice define um `WHERE` sargável.
```sql
\di+ nome_da_tabela*
-- ou:
SELECT indexname, indexdef FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'nome_da_tabela';
```

### Etapa 4 — Montar a query (sargável)

- Escreva o predicado sobre a **coluna indexada "nua"** (sem função em cima dela) e com
  bound **pré-computado** — nada de `WHERE date(created_at) = ...` ou `WHERE col + x > y`;
  use `created_at >= $1`.
- **Zero `SELECT *`** — liste colunas (ver Metade A §2).
- **Parametrize** todo valor (`$1`, `:campo`) — nunca interpole string na query.
- Em tabela grande, comece com `LIMIT`; se a query for pesada, rode `EXPLAIN` antes.

### Etapa 5 — Executar

Rode, confira a contagem/linhas contra o esperado, e só então interprete o resultado.
Se foi execução de escrita em produção, siga o gate de produção abaixo e registre a
mudança conforme a convenção de log do projeto.

---

## Gate de Produção (inegociável)

Toda execução contra o ambiente de **produção** — seja ele identificado no Project
Profile como `prod`, `production`, ou equivalente — exige:

1. **Validação humana explícita** — nunca conecte ou execute em produção por iniciativa
   própria; declare o que vai rodar e aguarde confirmação explícita antes de prosseguir.
2. **Validar em stage/homologação primeiro** — toda query/migration roda e é conferida
   no ambiente não-produtivo antes de chegar perto de produção, salvo leitura pontual que
   exige o número real de produção.
3. **Contar linhas-alvo antes de escrever** — todo `UPDATE`/`DELETE` é precedido de um
   `SELECT COUNT(*)` com a **mesma condição**, para comparar contra o efeito esperado.
4. **Envelopar toda escrita em transação explícita**:
   ```sql
   BEGIN;
   SELECT count(*) FROM t WHERE <mesma condição do UPDATE/DELETE>;  -- 1. cheque o alvo
   UPDATE t SET ... WHERE <condição>;                                -- 2. mute
   -- 3. confira linhas afetadas vs. esperado
   COMMIT;   -- ou ROLLBACK; se algo divergir
   ```
5. **Nunca `UPDATE`/`DELETE` sem `WHERE`** — e o `WHERE` deve bater com a contagem do
   passo 3.
6. **Sem DDL destrutivo improvisado** — `DROP`/`TRUNCATE`/`ALTER ... DROP COLUMN` só via
   migration revisada (par up/down), nunca solto numa sessão interativa.
7. **Confirmar o sinal de ambiente** antes de digitar qualquer comando de escrita — o
   sinal concreto (prompt colorido, banner, nome de host) vem do projeto; na dúvida,
   rode o comando de "conninfo" do dialeto antes de prosseguir.
8. **Logar a mudança** — toda mudança de dado em produção é registrada (o que rodou, por
   quê, linhas afetadas, quem autorizou) na convenção de memória/log do projeto.

Predicados seguem sargáveis mesmo em produção (Etapa 3/4) — volume real amplifica o custo
de uma varredura completa.

---

## Migrations — por Existência, não por Version

Aplicar migrations cegamente por número de versão é frágil: numeração fora de ordem,
aplicação manual fora de banda, ou deploy parcial deixam o tracking de version mentindo
sobre o estado real do schema.

**Regra:** antes de aplicar qualquer migration, **sempre valide se a estrutura-alvo já
existe** — inspecione a tabela/coluna/índice/constraint que a migration cria ou altera.
Só aplique o DDL se a estrutura ainda não existir. Idempotência primeiro; atualização do
tracking de version depois.

### Passo a passo

1. **Leia o estado de tracking atual** no ambiente alvo (a tabela de tracking vem de
   `database.migrations_table` no Project Profile):
   ```sql
   SELECT version, dirty FROM <migrations_table>;
   ```
   Se o flag `dirty`/equivalente estiver ligado: **PARE**. A última aplicação falhou no
   meio — resolva o estado sujo antes de qualquer migration nova.
2. **Liste as migrations do repositório** e identifique quais estão pendentes comparando
   contra o tracking.
3. **Antes de aplicar cada uma, valide por existência** — mesmo dentro da sequência
   normal, não só nos casos fora de ordem:
   ```sql
   \d nome_da_tabela                                    -- a coluna/constraint já existe?
   SELECT column_name FROM information_schema.columns
   WHERE table_name = 'nome_da_tabela' AND column_name = 'coluna_da_migration';
   SELECT indexname FROM pg_indexes WHERE indexname = 'indice_da_migration';
   ```
   - **Já existe** → não reaplique o DDL (evita erro/efeito duplicado); apenas avance o
     tracking de version para não perdê-lo.
   - **Ainda não existe** → aplique normalmente.
4. **Valide em stage/homologação primeiro** — aplique `up`, confira o efeito, teste o
   `down` quando viável. Só então cogite produção (com o Gate de Produção acima).
5. **Aplique em ordem crescente**, uma a uma. Após cada `up` bem-sucedido, **atualize o
   tracking** para a nova última versão — nunca pule esse passo, é ele que impede
   reaplicar ou perder migrations:
   ```sql
   UPDATE <migrations_table> SET version = <numero_aplicado>, dirty = false;
   ```
6. **Confirme ao final**: o tracking reflete a última migration aplicada, `dirty = false`.
7. **Migrations aditivas** usam a forma idempotente do dialeto (`ADD COLUMN IF NOT
   EXISTS` ou equivalente) para serem re-executáveis com segurança.
8. **Registre**: ambiente, faixa de versões aplicada, data — na convenção de
   memória/log do projeto.

---

## Checklist rápido

**Disciplina de query (Metade A):**
- [ ] Toda query SQL fixa é `const` nomeado — nenhuma string de query inline no corpo do método
- [ ] Zero `SELECT *` — todo SELECT lista colunas explicitamente via const de colunas
- [ ] Todo valor é `$N`/`:param` — nenhuma interpolação de string na query, nem para números
- [ ] Sem `COALESCE` em coluna já mapeada para tipo opcional no código
- [ ] Arquivo de teste de integração existe e cobre todos os métodos públicos do repositório
- [ ] Testes de SQL injection cobrem todo parâmetro string/opcional-de-string
- [ ] Campos nullable novos usam o wrapper `Null[T]` do projeto onde correção de JSON importa

**Fluxo de execução (Metade B):**
- [ ] Preflight de conexão passou (ou o onboarding foi emitido e a conexão corrigida)?
- [ ] Descobri o schema AO VIVO no host (tabelas → schema → indexes) — sem dicionário estático?
- [ ] Segui a ordem obrigatória (tabelas → schema → indexes → query → executar)?
- [ ] É leitura? → rodei no ambiente não-produtivo por padrão?
- [ ] É escrita ou é produção? → validei antes em ambiente não-produtivo?
- [ ] É produção? → tenho validação humana explícita?
- [ ] Escrita envelopada em transação, com contagem do alvo antes?
- [ ] `WHERE` presente e batendo com a contagem esperada; sem `SELECT *`; valores parametrizados?
- [ ] Migration: validei **existência** da estrutura-alvo antes de aplicar (não só a ordem de version)?
- [ ] Migration aplicada? → atualizei o tracking de version na mesma operação?
- [ ] Mudança de dado em produção registrada conforme a convenção de log do projeto?

---

## Fora de escopo desta skill

Nomes concretos de conexão, dialeto real, comandos de discovery exatos, nome da tabela de
tracking de migration, e o sinal concreto de "isto é produção" — tudo isso vem do bloco
`database` do Project Profile (`CLAUDE.md` / `AGENTS.md`). Regras de segurança específicas de
produto sobre dados financeiros/sensíveis (ex.: locks nomeados de domínio) também ficam no
Project Profile do projeto, não nesta skill.
