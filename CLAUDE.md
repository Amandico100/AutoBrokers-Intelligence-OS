# CLAUDE.md — Regras invioláveis de execução do AutoBrokers Intelligence OS

> Porta de entrada obrigatória de toda sessão. **Não substitui** as SPECs — obriga a lê-las na ordem certa.
> **v1.0** · 25/07/2026 · commit base auditado `3c8c752`

## 1. O produto

O **AutoBrokers.ai** é um SaaS multi-tenant verticalizado para corretoras de seguros. Não é um chatbot com ferramentas: é o **sistema operacional de trabalho da corretora**. Recebe um resultado desejado, monta o contexto correto, escolhe a Skill adequada, carrega só as ferramentas necessárias, executa em etapas duráveis, pede aprovação quando a ação é sensível, gera um Artifact profissional, entrega pelo canal escolhido e mede o resultado.

```text
O corretor descreve o que precisa.
O AutoBrokers transforma o pedido em trabalho governado.
O sistema executa, comprova, entrega e acompanha o resultado.
```

O corretor não compra ferramenta nem Skill. Compra **trabalho pronto, tempo recuperado e dinheiro**.

Nome oficial do agente central: **AutoBrokers**. "Jarvys/Jarvis" é metáfora externa — nunca aparece em UI, código, tabela ou documentação canônica. **Smith** é o runtime técnico invisível, não é marca.

## 2. Bootstrap de sessão — nesta ordem

1. [`docs/canon/EXECUTION-MASTER-PLAN.md`](docs/canon/EXECUTION-MASTER-PLAN.md) — onde estamos.
2. [`docs/canon/FOUNDER-DECISIONS.md`](docs/canon/FOUNDER-DECISIONS.md) — o que já foi decidido.
3. [`docs/canon/GLOSSARIO.md`](docs/canon/GLOSSARIO.md) — **um termo, uma definição.** Se dois documentos discordarem, este vence.
   · [`docs/canon/ONTOLOGIA-DO-TRABALHO.md`](docs/canon/ONTOLOGIA-DO-TRABALHO.md) — **o que é cada coisa e onde mora.** Antes de criar qualquer peça.
   · [`docs/canon/CAMADAS-DE-CONEXAO.md`](docs/canon/CAMADAS-DE-CONEXAO.md) — **quem paga, quem conecta, quem usa.** Antes de criar conector.
   · [`docs/canon/QUANDO-OFERECER-AUTOMACAO.md`](docs/canon/QUANDO-OFERECER-AUTOMACAO.md) — **quando o chat oferece automatizar, e quando fica quieto.**
   · [`docs/canon/PORTAIS-E-CORREDORES.md`](docs/canon/PORTAIS-E-CORREDORES.md) — **portal, corredor e Atlas: qual é qual.**
   · [`docs/canon/O-ATLAS-E-UM-SO-E-E-DE-TODAS.md`](docs/canon/O-ATLAS-E-UM-SO-E-E-DE-TODAS.md) — **o Atlas é UM só, de todas as corretoras.** Antes de tocar em `ura_maps`, no Tecelão, em playbook, corredor ou prompt de atendimento.
   · [`docs/canon/PENDENCIAS.md`](docs/canon/PENDENCIAS.md) — **o que ficou pendente, e o que destrava cada coisa.**
4. [`docs/canon/README.md`](docs/canon/README.md) — índice canônico.
5. A SPEC da etapa atual + **SPEC-052** e **SPEC-053**, sempre.
6. [`docs/canon/MIGRATIONS-AUTHORITY.md`](docs/canon/MIGRATIONS-AUTHORITY.md) — **antes de qualquer SQL**.

Preflight: `git rev-parse --show-toplevel` (deve ser `AutoBrokers-Opus-Exec`) · `git branch --show-current` · `git rev-parse HEAD` (registrar no relatório) · `git status --short` (limpo ao iniciar).

## 3. Ordem de autoridade

```text
CLAUDE.md (processo)
→ SPEC-052 (cérebro: conhecimento, memória, contexto, aprendizagem)
→ SPEC-053 (Work OS: harness, contratos, fronteiras)
→ 054 schema/segurança · 055 Work Runs/HITL · 056 Skills/Tools
→ 057 Artifacts · 058 Auxiliares/Rotinas · 059 Intelligence Fabric
→ 060 Research · 061 Control Plane · 062 evals/billing/go-live
→ ADRs e SPECs históricas apenas quando não conflitarem
```

Em ambiguidade material: **pare e registre** em `FOUNDER-DECISIONS.md`. Não decida arquitetura sozinho.

## 4. Memórias superadas

Instruções baseadas em **SPEC-013** (Studio/releases/registry, `CORE_CHAT_MODEL`, nomenclatura "SERGIO/Even") e interpretações antigas da **SPEC-014** que tratem o Capability Registry como autoridade final de Skills/tools **não são autoridade**. SPEC-013 não existe em `docs/canon/specs/`. SPEC-014 é fundação histórica; a **SPEC-056** prevalece. Memórias que digam "ship to prod" sem gate são inválidas enquanto houver P0 aberto. **Conflito entre memória global e este arquivo: este arquivo vence.**

## 5. Proibições estruturais

Nunca criar em paralelo ao existente: runtime · RAG · memória · publisher · scheduler · executor · Skill Registry · Tool Gateway · Artifact Hub · Auxiliary Factory · Intelligence Fabric · Research Orchestrator · Control Plane · Eval Platform · Billing Engine · Ledger · Readiness Engine.

**Consolidar e migrar antes de duplicar.** Refazer peça mal construída é permitido; criar remendo ao lado dela, não.

## 6. Autoridades e ontologia

| Camada | Papel | | Termo | Significado |
|---|---|---|---|---|
| **Supabase** | verdade operacional durável | | **Outcome** | resultado de negócio desejado |
| **Redis** | transitório: fila, lock, lease, cache | | **Skill** | procedimento versionado |
| **Qdrant** | índice derivado e reconstruível | | **Capability** | poder governável |
| **MinIO** | bytes: documentos e artifacts | | **Tool** | implementação técnica |
| **Vault** | segredos e conexões | | **Work Run** | execução universal |
| **Capability Registry** | poderes | | **Approval** | decisão humana vinculada |
| **Skill Registry** | procedimentos | | **Artifact** | resultado de 1ª classe |
| **Tool Gateway** | seleção/execução de tools | | **Auxiliar** | trabalhador instalado |
| **Work Run** | execução durável | | **Rotina** | gatilho |
| **Artifact Hub** | entregáveis | | **Finding** | separa fato de inferência |

Auxiliar **não** é Rotina. Rotina **não** é Agent. Skill **não** é RAG. MCP **não** é produto. Approval **não** é frase de prompt. Artifact **não** é arquivo órfão.

## 7. Multi-tenant

```text
RLS + filtro obrigatório no repository/service
    + constraints e foreign keys
    + teste automático de isolamento com dois tenants reais
```

O backend usa **service role**: RLS sem policy **não protege nada** contra erro de filtro no código. Nenhum dado atravessa tenants. Nenhum segredo em log, blueprint, artifact ou RAG.

## 8. Migrations

Diretório canônico de **novas** migrations: `backend/supabase/migrations/`.

**Leia [`docs/canon/MIGRATIONS-AUTHORITY.md`](docs/canon/MIGRATIONS-AUTHORITY.md) antes de qualquer SQL.** O repositório **não** é a fonte completa do schema: 9 versões aplicadas não têm arquivo e 16 arquivos não têm versão aplicada.

Proibido sem manifesto aprovado: mover, renomear, apagar ou reaplicar migration existente. Proibido sempre: aplicar `schema_completo.sql`, `upgrade_v6.2.sql` ou `storage_buckets.sql`. Toda migration: idempotente · expand-first · com **APPLY / VERIFY / ROLLBACK** escritos **antes** de rodar.

## 9. Método de execução

- Um **bloco** é uma **entrega coesa** com gate verificável — não necessariamente uma sessão nem um commit.
- Um bloco pode ter vários commits, várias sessões e migrations em momentos distintos.
- Uma **SPEC** tem: uma branch, um relatório final e um gate final.
- Gates internos são **automáticos**: aplicar → VERIFY → testes → verde → avançar.
- **Não** pedir aprovação manual do Founder entre todos os blocos.
- Pasta única `AutoBrokers-Opus-Exec`; uma branch por SPEC/pacote; recomendada uma sessão nova por SPEC.

### 9.1 Build verde **não** é prova de que a aplicação sobe

> Acrescentado em 02/08/2026, depois que o produto ficou **1h40 fora do ar** com
> todos os gates verdes.

Uma pasta `[slug]` nasceu ao lado de uma `[templateId]` na mesma posição da
árvore de rotas. O Next.js exige **um nome de parâmetro por posição**. Passaram:
`next build` (287 rotas), `tsc --noEmit`, 111 testes, a imagem Docker e o
`Ready in 1253ms` do contêiner. A linha seguinte foi
`getSortedRoutes: You cannot use different slug names…` — e **todas** as rotas
passaram a devolver 500, inclusive a página de 404.

**Todos os gates paravam antes de ligar o servidor.**

Antes de declarar gate verde numa SPEC que mexeu em `app/`, `middleware.ts`,
`instrumentation.ts`, `next.config.js` ou variáveis de ambiente:

```
npm run test:rotas-montam     a tabela de rotas monta (getSortedRoutes real)
next start + 1 requisição     o servidor RESPONDE — não só compila
```

Uma rota que responde 200 vale mais que um build de 287 rotas.

**E o sintoma engana:** `public/` continua servindo 200 porque o servidor de
estáticos não passa pelo roteador. Parece "algumas telas quebradas"; é o produto
inteiro. Ao investigar queda, o primeiro teste é **rota que executa código**
(`/api/…`), nunca um arquivo.

### 9.2 Medir vence deduzir — e toda bateria precisa de controle

> Acrescentado em 03/08/2026, depois que o envio de formulário nativo do
> WhatsApp foi resolvido por **medição**, não por leitura.

Havia **uma** captura real do que se queria reproduzir. Um acervo de um permite
comparar; **não permite conferir hipótese**. Deduzir a diferença por leitura era
impossível — e cada palpite errado custava um ciclo de build inteiro.

O que funcionou:

```
varie UM fator por vez        version · nós biz · body · embrulho · segredo
inclua uma linha de CONTROLE  repete a rodada anterior
pare no primeiro que passar
```

📊 Cinco formas deram o mesmo erro → **fator que não muda o resultado não é a
causa**, e o payload inteiro caiu de uma vez. A sexta passou.

**A linha de controle é o que dá direito à conclusão.** Ela deu o mesmo erro de
antes, então o mérito foi do fator que mudou e de mais nada. Sem ela, um acerto
se credita ao lugar errado — e se constrói em cima de uma causa que não era.

E leia o erro **na fonte**: `479` não foi pesquisado, foi lido no comentário da
biblioteca que o documenta.

### 9.3 Teste que guarda verdade vencida é pior que teste nenhum

No mesmo dia, dois testes tiveram de ser **atualizados**: eles afirmavam que não
existia canal para responder formulário. Era verdade — até o canal existir.

Quando um fato muda, o teste muda com ele, e **a lição migra em vez de morrer**:
a recusa limpa continua sendo testada, agora desligando a rota de propósito.
Manter a afirmação vencida só ensinaria a ignorar teste.

**Corolário:** um guarda que não tem como falhar não guarda nada. Quando o teste
comparar duas coisas, prove que elas **conseguem** ser diferentes.


### 9.4 Teste de corredor chama o motor — teste que chama o regex guarda o regex

> Acrescentado em 21/08/2026, depois que **72 asserções verdes** conviveram com um
> agendamento que nunca chegava ao cliente.

A rota da máquina de lavar tinha teste dedicado, 401 linhas, 72 asserções e linhas
de controle de verdade. A âncora `schedule_agendado` estava correta. E o segurado
recebeu *"sua assistência foi aberta"* sem data e sem período — porque
`extract_capture_anchors` lia cinco chaves e **nunca aquela**.

📊 O arquivo tinha **zero** chamadas ao motor. Dois helpers próprios rodavam regex
direto: um sobre `capture_anchors`, outro **reimplementando** `match_ura_step`.
Provavam que os regexes casavam. Não provavam que alguém os usava.

```
✅  CP.extract_capture_anchors(playbook, tela_real)
❌  re.search(playbook["capture_anchors"]["schedule"], tela_real)
```

**Vale para toda peça declarativa:** âncora, passo, gatilho, slot, tecla. O que se
afirma é o comportamento do **MOTOR** sobre o texto **REAL**.

**Exceção:** regex sobre a âncora **como texto**, para conferir a FORMA da
declaração (ex.: *"nenhuma âncora exige `*` literal"*), é legítimo — o alvo é a
captura que substitui o motor, não a inspeção da declaração.

**E o texto da tela vem do acervo, não da imaginação.** 📊 O passo
`numero_residencia` exigiu por semanas uma frase com ZERO ocorrências em 28.096
eventos.

#### 🔴 O corolário que a execução da SPEC-083 acrescentou: MOTOR DE REGEX TEM DIALETO

O helper trocado pelo motor foi só metade. A outra metade apareceu três vezes na
mesma execução, sempre igual: **um padrão medido com um motor e aplicado com
outro é um padrão sobre outra coisa.**

```
📊 medido em SQL, aplicado em Python
   `.` casa `
` no Postgres e NÃO casa em Python.
   Quatro padrões de ramo caíam de 37/26/4/3 sessões para ZERO, em silêncio —
   e a régua não classificava a própria sessão que a validou.

📊 medido em texto CRU, aplicado em texto NORMALIZADO
   `_norm` remove o `*` do negrito. O padrão-ouro `\*servi[çc]o\*?:` caía de
   112 sessões para ZERO.

📊 medido com acento, aplicado depois do `_norm`
   `necess[áa]rio` funciona; `necessário` sozinho perde metade do acervo.
```

**Antes de confiar num número que veio de outra ferramenta, rode-o na ferramenta
que vai usá-lo.** E o guarda que fecha a porta: um teste que exija **ZERO** para o
padrão sem a flag — porque é assim que se descobre que a flag era o que o fazia
funcionar.


## 10. Condições legítimas de parada

Pare e registre **somente** por: (1) risco de perda de dados · (2) decisão comercial ou de precificação · (3) conflito canônico · (4) P0/P1 de segurança ou cross-tenant · (5) ação física do Founder (QR, passkey, acesso, pagamento) · (6) mudança material de escopo · (7) custo extraordinário · (8) falta de acesso indispensável.

Fora disso: complete o bloco, execute o VERIFY e avance.

## 11. Mudanças além do texto da SPEC

Vão para [`docs/canon/CHANGE-ADDENDA.md`](docs/canon/CHANGE-ADDENDA.md), classificadas como **BLOCKER · ESSENCIAL · VALIOSA · FUTURA**, com problema, evidência, consequência e autorização. **Escopo não pode ser reduzido sem decisão explícita do Founder** (D5) — sugestões de adiamento são propostas registradas, nunca execução. Nada é executado silenciosamente.

### 11.1 O que fica pendente vai para [`PENDENCIAS.md`](docs/canon/PENDENCIAS.md)

**Toda SPEC que termina deixa lá o que não coube nela** — chave de API que
falta, integração que espera terceiro, tela que ainda mora no lugar errado,
tabela sem escritor. Cada entrada diz **o que destrava**, **de quem é** (🧑
Founder ou 🤖 execução) e **o que custa esquecer**.

> **Deixar pronto e desligado é aceitável. Deixar pronto e não anotado, não.**

Nada sai da lista sem estar feito ou sem uma decisão registrada.

## 12. Relatório por SPEC

Use [`docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE.md`](docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE.md). Sempre: commit inicial e final · arquivos alterados · migrations com APPLY/VERIFY/ROLLBACK · testes com **saída real** · o que ficou fora e por quê · canário Amandus → Resulta → AutoFleet · riscos remanescentes · declaração de que nenhum motor paralelo foi criado.

Separe **FATO**, **INFERÊNCIA** e **RECOMENDAÇÃO**. Não afirme que algo funciona só porque existe código.

### 12.1 Número medido e número ilustrativo têm marcação obrigatória

> Acrescentado em 02/08/2026, depois que um número de exemplo virou "achado do
> produto" e atravessou seis documentos como se fosse medição.

| Marca | Significado | Exigência |
|---|---|---|
| 📊 | **medido** | data, fonte e a query/comando que produziu o número |
| 💭 | **ilustrativo** | exemplo de copy ou hipótese — **nunca citável como fato** |

**Vale em SPEC, relatório, prompt, handoff e commit.** Número sem marca, em
documento novo, é defeito de revisão.

**E o corolário que fecha a porta:** se o nome de um campo mente sobre o que ele
guarda (`premio` que é parcela vencida), **conserte o campo** — não só o texto.
O texto errado é o sintoma; o nome errado é a causa, e ela reinfecta todo leitor
seguinte.

## 13. Regras finais

1. Não alterar produção antes do preflight de infraestrutura (P1 pendente).
2. Não usar `latest` em imagem crítica.
3. Não exibir segredo — apenas presença/ausência.
4. Não apagar legado antes de backfill e prova.
5. Não apagar memórias globais, worktrees antigos nem o material de INTAKE.
6. Não inventar preço, plano, invoice ou cobrança fora da SPEC-062.
7. Não presumir implementação só porque existe SPEC.
8. Não fazer merge na `main` sem gate final da SPEC.
