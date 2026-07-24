# Índice e autoridade das SPECs canônicas

> [!IMPORTANT]
> Para qualquer tarefa relacionada a conhecimento, RAG, memória, Context Assembly, aprendizagem, ferramentas, Skills, conectores, MCPs, Auxiliares, Rotinas, Work Runs, approvals, artifacts ou Portal Admin, leia primeiro as SPECs **052** e **053**.

## Autoridade atual

1. `SPEC-052-cerebro-cognitivo-unificado-autobrokers.md` — arquitetura cognitiva soberana: conhecimento, memória, contexto, aprendizagem e cérebro unificado.
2. `SPEC-053-autobrokers-work-os-core-harness.md` — arquitetura soberana do Work OS: Core Harness, Skills, Tool Gateway, execução durável, Auxiliares, Rotinas, artifacts e Control Plane.
3. [`SPEC-054-foundation-hardening-schema-governance.md`](SPEC-054-foundation-hardening-schema-governance.md) — SPEC canônica e autorizada para execução: fechamento P0, Storage privado, baseline reproduzível, integridade multi-tenant, hardening de HTTP/MCP, Authority Strict progressivo e idempotência preparatória.
4. SPECs posteriores explicitamente subordinadas às SPECs 052, 053 e 054.
5. SPECs anteriores apenas quando não houver conflito.

## Próxima sequência subordinada

- `SPEC-055` — Durable Work Runs, Queue, Checkpoints & HITL;
- `SPEC-056` — Skill Registry & Tool Gateway;
- `SPEC-057` — Artifact Hub & Report Studio;
- `SPEC-058` — Auxiliary & Routine Factory;
- `SPEC-059` — Briefing, Proatividade & Garimpo v3;
- `SPEC-060` — Research Intelligence;
- `SPEC-061` — Portal Admin Control Plane;
- `SPEC-062` — Evals, Billing, Rollout & Production Readiness.

## SPEC-054 — auditoria e execução

- [`../audits/AUDIT-SPEC-054-foundation-hardening-schema-governance-2026-07-24.md`](../audits/AUDIT-SPEC-054-foundation-hardening-schema-governance-2026-07-24.md) — censo read-only do Supabase e da `main`, cobrindo schema vivo, migrations, RLS, funções, Storage, multi-tenancy, SSRF, MCP, Authority Strict, idempotência, performance, rollout e critérios de aceite.
- [`SPEC-054-foundation-hardening-schema-governance.md`](SPEC-054-foundation-hardening-schema-governance.md) — documento de implementação autorizado. Deve ser executado em três blocos macro, com APPLY/VERIFY/ROLLBACK, gates automáticos e canário Amandus → Resulta → AutoFleet.

A auditoria deve ser lida antes da SPEC. A SPEC governa a implementação.

## SPECs parcialmente superadas

As seguintes SPECs permanecem disponíveis como histórico e detalhamento técnico, mas não são mais autoridade soberana quando houver conflito:

### Arquitetura cognitiva — prevalece SPEC-052

- `../SPEC-003-knowledge-rag-memory.md`;
- `../SPEC-004-agent-intelligence-context-architecture.md`;
- `../SPEC-008-producao-global-autobrokers.md`;
- `../SPEC-010-rag-knowledge-memory-curation-autobrokers-smith.md`;
- `SPEC-034-harness-robusto-multiagente-atendimento.md`;
- `SPEC-040-ESPELHO-VISAO-OPERACIONAL-E-CENTRAL-COMPLETA.md` e documentos relacionados;
- `SPEC-044-tres-camadas-global-corretora-usuario.md`.

### Work OS, Auxiliares e Rotinas — prevalece SPEC-053

- `../SPEC-002-auxiliares-runtime-smith.md`, somente onde conflitar com a ontologia e o modelo universal de Work Run;
- `SPEC-019-rotinas-auxiliares-claude-parity.md`, especialmente a equivalência antiga entre Auxiliares e Rotinas;
- seções históricas de `SPEC-034` sobre harness quando conflitarem com o Tool Gateway, Skills, HITL ou execução durável.

## Regra para agentes de desenvolvimento

```text
Leia a SPEC-052 para conhecimento, memória, contexto e aprendizagem.
Leia a SPEC-053 para harness, Skills, tools, MCPs, Auxiliares, Rotinas,
Work Runs, approvals, artifacts e Portal Admin.
Leia a SPEC-054 antes de alterar schema, migrations, RLS, Storage,
service-role, HTTP egress, MCP sandbox, Authority Strict ou idempotência.

Não crie RAG, memória, publisher, runtime, scheduler, executor,
Artifact Hub ou catálogo paralelo.
Não use decisões históricas que contradigam as SPECs 052, 053 e 054.
Em ambiguidade, pare e solicite decisão do CEO/Founder.
```

## Nome oficial

O chat principal e agente central do produto se chama **AutoBrokers**.

“Jarvys/Jarvis” é apenas uma metáfora externa para explicar a ambição de produto e não deve ser usado em UI, código de produto, agentes ou documentação canônica como nome oficial.
