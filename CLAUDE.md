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
3. [`docs/canon/README.md`](docs/canon/README.md) — índice canônico.
4. A SPEC da etapa atual + **SPEC-052** e **SPEC-053**, sempre.
5. [`docs/canon/MIGRATIONS-AUTHORITY.md`](docs/canon/MIGRATIONS-AUTHORITY.md) — **antes de qualquer SQL**.

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

## 10. Condições legítimas de parada

Pare e registre **somente** por: (1) risco de perda de dados · (2) decisão comercial ou de precificação · (3) conflito canônico · (4) P0/P1 de segurança ou cross-tenant · (5) ação física do Founder (QR, passkey, acesso, pagamento) · (6) mudança material de escopo · (7) custo extraordinário · (8) falta de acesso indispensável.

Fora disso: complete o bloco, execute o VERIFY e avance.

## 11. Mudanças além do texto da SPEC

Vão para [`docs/canon/CHANGE-ADDENDA.md`](docs/canon/CHANGE-ADDENDA.md), classificadas como **BLOCKER · ESSENCIAL · VALIOSA · FUTURA**, com problema, evidência, consequência e autorização. **Escopo não pode ser reduzido sem decisão explícita do Founder** (D5) — sugestões de adiamento são propostas registradas, nunca execução. Nada é executado silenciosamente.

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
