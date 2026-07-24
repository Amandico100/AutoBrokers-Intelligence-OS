# Índice e autoridade das SPECs canônicas

> [!IMPORTANT]
> Para qualquer tarefa relacionada a conhecimento, RAG, memória, Context Assembly, aprendizagem, ferramentas, Skills, conectores, MCPs, Auxiliares, Rotinas, Work Runs, approvals, artifacts ou Portal Admin, leia primeiro as SPECs **052** e **053**.

## Autoridade atual

1. `SPEC-052-cerebro-cognitivo-unificado-autobrokers.md` — arquitetura cognitiva soberana: conhecimento, memória, contexto, aprendizagem e cérebro unificado.
2. `SPEC-053-autobrokers-work-os-core-harness.md` — arquitetura soberana do Work OS: Core Harness, Skills, Tool Gateway, execução durável, Auxiliares, Rotinas, artifacts e Control Plane.
3. [`SPEC-054-foundation-hardening-schema-governance.md`](SPEC-054-foundation-hardening-schema-governance.md) — fechamento P0, Storage privado, baseline reproduzível, integridade multi-tenant, hardening de HTTP/MCP, Authority Strict progressivo e idempotência preparatória.
4. [`SPEC-055-durable-work-runs-queue-checkpoints-hitl.md`](SPEC-055-durable-work-runs-queue-checkpoints-hitl.md) — execução universal de lançamento: Work Runs, steps, attempts, Redis Streams, worker Smith, leases, checkpoints, HITL, approvals, side effects idempotentes e integração com Rotinas, Auxiliares e Portais.
5. [`SPEC-056-skill-registry-tool-gateway.md`](SPEC-056-skill-registry-tool-gateway.md) — catálogo canônico e versionado de Skills, Capability Packs e Tool Releases; Tool Gateway único; seleção dinâmica; migração de native/HTTP/MCP/Portal/delegation; biblioteca inicial de Skills e ativação em produção.
6. SPECs posteriores explicitamente subordinadas às SPECs 052–056.
7. SPECs anteriores apenas quando não houver conflito.

## Próxima sequência subordinada

- `SPEC-057` — Artifact Hub & Report Studio;
- `SPEC-058` — Auxiliary & Routine Factory;
- `SPEC-059` — Briefing, Proatividade & Garimpo v3;
- `SPEC-060` — Research Intelligence;
- `SPEC-061` — Portal Admin Control Plane;
- `SPEC-062` — Evals, Billing, Rollout & Production Readiness.

## SPEC-054 — auditoria e execução

- [`../audits/AUDIT-SPEC-054-foundation-hardening-schema-governance-2026-07-24.md`](../audits/AUDIT-SPEC-054-foundation-hardening-schema-governance-2026-07-24.md) — censo read-only do Supabase e da `main`, cobrindo schema vivo, migrations, RLS, funções, Storage, multi-tenancy, SSRF, MCP, Authority Strict, idempotência, performance, rollout e critérios de aceite.
- [`SPEC-054-foundation-hardening-schema-governance.md`](SPEC-054-foundation-hardening-schema-governance.md) — documento de implementação autorizado em três blocos macro, com APPLY/VERIFY/ROLLBACK e canário Amandus → Resulta → AutoFleet.

## SPEC-055 — execução durável de lançamento

- [`SPEC-055-durable-work-runs-queue-checkpoints-hitl.md`](SPEC-055-durable-work-runs-queue-checkpoints-hitl.md) — documento de implementação autorizado em três blocos macro. Ao final, `work_runs` deve ser a autoridade universal ativa, o worker deve estar em produção e os caminhos de Rotinas, Auxiliares e Portais devem criar/atualizar Work Runs sem execução paralela.

A SPEC-055 não é um laboratório. Testes, canários e flags são gates internos da mesma entrega de lançamento e não justificam deixar a funcionalidade permanentemente desligada.

## SPEC-056 — Skills e Tool Gateway de lançamento

- [`SPEC-056-skill-registry-tool-gateway.md`](SPEC-056-skill-registry-tool-gateway.md) — documento de implementação autorizado em três blocos macro. Ao final, o Capability Registry existente continua como autoridade, o Skill Registry complementa a governança, o Tool Gateway é o único caminho de seleção/execução, Skills iniciais estão publicadas e native/HTTP/MCP/Portal/delegation não mantêm autorização paralela.

A SPEC-056 também não é um catálogo visual ou uma fase beta. A entrega só termina quando Skills reais forem usadas pelo Core e pelos Work Runs em produção.

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

### Capabilities, Skills e tools — prevalece SPEC-056

- `../SPEC-014-capability-registry-knowledge-os.md` continua como fundação histórica do Registry, mas a SPEC-056 prevalece em Skill Releases, Capability Packs, Tool Definitions/Releases, seleção dinâmica, Tool Gateway e cutover das autoridades legadas;
- definições hardcoded de Portal Skills continuam como evidência histórica, não como catálogo canônico;
- autorização por `tools_config`, menção em prompt, row isolada de HTTP tool ou descoberta automática MCP é superada pelo Tool Gateway.

## Regra para agentes de desenvolvimento

```text
Leia a SPEC-052 para conhecimento, memória, contexto e aprendizagem.
Leia a SPEC-053 para Work OS, Auxiliares, Rotinas, artifacts e Control Plane.
Leia a SPEC-054 antes de alterar schema, migrations, RLS, Storage,
service-role, HTTP egress, MCP sandbox, Authority Strict ou idempotência.
Leia a SPEC-055 antes de alterar Work Runs, fila, worker, checkpoint,
HITL, approvals, side effects ou integração de execução.
Leia a SPEC-056 antes de alterar Skills, capabilities, toolsets,
HTTP/MCP/native/Portal tools, subagentes ou seleção dinâmica.

Não crie RAG, memória, publisher, runtime, scheduler, executor,
Skill Registry, Tool Gateway, Artifact Hub ou catálogo paralelo.
Não use decisões históricas que contradigam as SPECs 052–056.
Em ambiguidade, pare e solicite decisão do CEO/Founder.
```

## Nome oficial

O chat principal e agente central do produto se chama **AutoBrokers**.

“Jarvys/Jarvis” é apenas uma metáfora externa para explicar a ambição de produto e não deve ser usado em UI, código de produto, agentes ou documentação canônica como nome oficial.